from __future__ import annotations

import hashlib
import os
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aipinho.services.config_governance.workspace_permission_matrix_service import (
    ACTION_PERMISSION_ALIASES,
)
from aipinho.services.prompt_intelligence.workspace_reference_extractor_service import (
    WorkspaceReferenceExtractorService,
)


@dataclass(frozen=True)
class WorkspaceScopePermissionDecision:
    matched: bool
    status: str
    reason_code: str
    permission: str
    workspace_role: str | None
    root_path: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntentWorkspaceScopeService:
    """Builds request-scoped workspace roles and permissions from prompt intent."""

    READ_PERMISSIONS = {"read_file", "list_files", "copy_from"}
    MUTATION_PERMISSIONS = {"create_file", "modify_file", "apply_patch", "artifact_create"}
    EXECUTION_PERMISSIONS = {"shell_build", "shell_test", "script_execution"}

    def __init__(
        self,
        extractor: WorkspaceReferenceExtractorService | None = None,
    ) -> None:
        self.extractor = extractor or WorkspaceReferenceExtractorService()

    def resolve(
        self,
        *,
        prompt: str,
        workspace_hint: str | None,
        semantic_graph: dict[str, Any] | Any | None,
    ) -> dict[str, Any]:
        graph = self._graph(semantic_graph)
        refs = self.extractor.extract(prompt)
        normalized_prompt = self._normalize(prompt)
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()

        for ref in refs:
            path = str(ref.path).rstrip("\\").rstrip("/")
            key = self._norm_path(path)
            if key in seen:
                continue
            seen.add(key)
            role = str(ref.role or "unknown")
            if role == "unknown":
                role = self._fallback_role(
                    path=path,
                    workspace_hint=workspace_hint,
                    graph=graph,
                )
            kind = self._scope_kind(prompt, path)
            entries.append(
                self._entry(
                    path=path,
                    role=role,
                    kind=kind,
                    graph=graph,
                    normalized_prompt=normalized_prompt,
                    evidence=str(ref.evidence or "prompt_path_reference"),
                    confidence=float(ref.confidence or 0.5),
                )
            )

        if workspace_hint:
            hint_key = self._norm_path(workspace_hint)
            if hint_key not in seen:
                role = self._fallback_role(
                    path=workspace_hint,
                    workspace_hint=workspace_hint,
                    graph=graph,
                )
                entries.insert(
                    0,
                    self._entry(
                        path=workspace_hint,
                        role=role,
                        kind="project",
                        graph=graph,
                        normalized_prompt=normalized_prompt,
                        evidence="active_or_resolved_workspace_hint",
                        confidence=0.8,
                    ),
                )

        mutable = [item for item in entries if item["role"] == "target_mutable"]
        primary = None
        if workspace_hint:
            primary = next(
                (
                    item["path"]
                    for item in entries
                    if self._same_path(item["path"], workspace_hint)
                ),
                None,
            )
        if primary is None and mutable:
            primary = mutable[0]["path"]
        if primary is None and entries:
            primary = entries[0]["path"]

        readonly_roots = [
            item["path"] for item in entries if item["role"] == "source_readonly"
        ]
        library_roots = [
            item["path"]
            for item in entries
            if item["role"] == "source_readonly" and item["kind"] == "library"
        ]
        external_roots = [
            item["path"]
            for item in entries
            if item["path"] != primary and item["role"] == "source_readonly"
        ]
        readonly_flags = {
            item["path"]: item["role"] != "target_mutable" for item in entries
        }
        return {
            "version": 1,
            "source": "prompt_intent",
            "primary_workspace": primary,
            "scopes": entries,
            "mutable_roots": [item["path"] for item in mutable],
            "readonly_roots": readonly_roots,
            "library_roots": library_roots,
            "external_roots": external_roots,
            "readonly_flags": readonly_flags,
            "workspace_ids": [item["scope_id"] for item in entries],
        }

    def decide(
        self,
        *,
        contract: dict[str, Any] | None,
        path: str | None,
        permission: str,
    ) -> WorkspaceScopePermissionDecision:
        canonical = ACTION_PERMISSION_ALIASES.get(permission, permission)
        entry = self.scope_for_path(contract=contract, path=path)
        if entry is None:
            return WorkspaceScopePermissionDecision(
                matched=False,
                status="unresolved",
                reason_code="intent_workspace_scope_not_matched",
                permission=canonical,
                workspace_role=None,
                root_path=None,
            )
        role = str(entry.get("role") or "unknown")
        declared = set(entry.get("declared_permissions") or [])
        if canonical not in declared:
            return WorkspaceScopePermissionDecision(
                matched=True,
                status="denied",
                reason_code="permission_not_declared_by_prompt_scope",
                permission=canonical,
                workspace_role=role,
                root_path=str(entry.get("path") or ""),
            )
        status = (
            "allowed"
            if canonical in self.READ_PERMISSIONS
            else "approval_required"
        )
        return WorkspaceScopePermissionDecision(
            matched=True,
            status=status,
            reason_code=(
                "permission_declared_by_prompt_scope"
                if status == "allowed"
                else "permission_declared_requires_governance"
            ),
            permission=canonical,
            workspace_role=role,
            root_path=str(entry.get("path") or ""),
        )

    def scope_for_path(
        self,
        *,
        contract: dict[str, Any] | None,
        path: str | None,
    ) -> dict[str, Any] | None:
        if not path or not isinstance(contract, dict):
            return None
        candidates = [
            item
            for item in contract.get("scopes", []) or []
            if isinstance(item, dict)
            and item.get("path")
            and self._is_under(path, str(item["path"]))
        ]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda item: len(self._norm_path(str(item["path"]))),
            reverse=True,
        )[0]

    def _entry(
        self,
        *,
        path: str,
        role: str,
        kind: str,
        graph: dict[str, Any],
        normalized_prompt: str,
        evidence: str,
        confidence: float,
    ) -> dict[str, Any]:
        if role not in {"source_readonly", "target_mutable"}:
            role = "source_readonly" if graph.get("readonly_contract") else "target_mutable"
        permissions = set(self.READ_PERMISSIONS)
        if role == "target_mutable":
            if graph.get("mutation_intent"):
                permissions.update(self.MUTATION_PERMISSIONS)
            if graph.get("execution_intent") or "build_execution" in set(
                graph.get("requested_effects", []) or []
            ):
                permissions.update(self.EXECUTION_PERMISSIONS)
            git_context = (
                "git " in normalized_prompt
                or " git" in normalized_prompt
                or "commit" in normalized_prompt
                or "push" in normalized_prompt
            )
            if git_context:
                permissions.add("git_write")
            if "git commit" in normalized_prompt or (
                "commit" in normalized_prompt and git_context
            ):
                permissions.add("git_commit")
            if "git push" in normalized_prompt or (
                "push" in normalized_prompt and git_context
            ):
                permissions.add("git_push")
            if any(
                term in normalized_prompt
                for term in (
                    "network",
                    "rede",
                    "http://",
                    "https://",
                    "download",
                    "baixar",
                    "curl ",
                    "wget ",
                    "git fetch",
                    "git pull",
                    "git push",
                )
            ):
                permissions.add("network_download")
        digest = hashlib.sha256(
            f"{self._norm_path(path)}|{role}".encode("utf-8")
        ).hexdigest()[:16]
        return {
            "scope_id": f"intent_workspace_{digest}",
            "path": path,
            "role": role,
            "kind": kind,
            "readonly": role == "source_readonly",
            "mutable": role == "target_mutable",
            "declared_permissions": sorted(permissions),
            "evidence": [evidence],
            "confidence": confidence,
        }

    def _fallback_role(
        self,
        *,
        path: str,
        workspace_hint: str | None,
        graph: dict[str, Any],
    ) -> str:
        if workspace_hint and self._same_path(path, workspace_hint):
            if graph.get("mutation_intent"):
                return "target_mutable"
            return "source_readonly"
        if graph.get("readonly_contract"):
            return "source_readonly"
        if graph.get("mutation_intent"):
            return "target_mutable"
        return "source_readonly"

    def _scope_kind(self, prompt: str, path: str) -> str:
        index = prompt.casefold().find(path.casefold())
        before = prompt[max(0, index - 180):index] if index >= 0 else ""
        normalized = self._normalize(before)
        if any(
            token in normalized
            for token in ("corpus", "biblioteca", "library", "dataset", "musicas", "media")
        ):
            return "library"
        return "project"

    def _graph(self, value: dict[str, Any] | Any | None) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return dict(value.model_dump(mode="json"))
        return {}

    def _normalize(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

    def _norm_path(self, value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def _same_path(self, left: str, right: str) -> bool:
        return self._norm_path(left) == self._norm_path(right)

    def _is_under(self, path: str, root: str) -> bool:
        normalized_path = self._norm_path(path)
        normalized_root = self._norm_path(root)
        return (
            normalized_path == normalized_root
            or normalized_path.startswith(normalized_root + os.sep)
        )
