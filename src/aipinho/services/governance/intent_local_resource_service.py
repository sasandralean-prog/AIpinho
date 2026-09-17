from __future__ import annotations

import hashlib
import os
import unicodedata
from pathlib import Path
from typing import Any

from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.services.prompt_intelligence.workspace_reference_extractor_service import (
    WorkspaceReferenceExtractorService,
)


class IntentLocalResourceService:
    """Compiles prompt-level local workspace references into mission resources.

    This service belongs to semantic ingress. Runtime enforcement must consume the
    frozen MissionContract resources and must never call this service or reparse
    the original prompt.
    """

    READ_PERMISSIONS = {"read_file", "list_files", "copy_from"}
    MUTATION_PERMISSIONS = {
        "create_directory",
        "create_file",
        "modify_file",
        "apply_patch",
        "artifact_create",
    }
    EXECUTION_PERMISSIONS = {
        "shell_readonly",
        "shell_build",
        "shell_test",
        "script_execution",
    }

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
    ) -> list[MissionResourceScope]:
        graph = self._graph(semantic_graph)
        references = self.extractor.extract(prompt)
        resources: list[MissionResourceScope] = []
        seen: set[str] = set()

        for reference in references:
            path = str(reference.path).rstrip("\\/")
            key = self._normalize_path(path)
            if key in seen:
                continue
            seen.add(key)
            kind = self._kind(prompt, path)
            role = str(reference.role or "unknown")
            if role == "workspace":
                role = "unknown"
            if role == "unknown":
                role = self._fallback_role(
                    path=path,
                    kind=kind,
                    workspace_hint=workspace_hint,
                    graph=graph,
                )
            resources.append(
                self._resource(
                    path=path,
                    role=role,
                    kind=kind,
                    graph=graph,
                    evidence=str(reference.evidence or "prompt_path_reference"),
                    confidence=float(reference.confidence or 0.5),
                )
            )

        if workspace_hint:
            hint_key = self._normalize_path(workspace_hint)
            if hint_key not in seen:
                resources.insert(
                    0,
                    self._resource(
                        path=workspace_hint,
                        role=self._fallback_role(
                            path=workspace_hint,
                            kind="project",
                            workspace_hint=workspace_hint,
                            graph=graph,
                        ),
                        kind="project",
                        graph=graph,
                        evidence="active_workspace_hint",
                        confidence=0.8,
                    ),
                )

        return sorted(resources, key=lambda item: item.resource_id)

    def primary_workspace(
        self,
        resources: list[MissionResourceScope],
        *,
        workspace_hint: str | None = None,
    ) -> str | None:
        if workspace_hint:
            for resource in resources:
                if resource.locator and self._same_path(resource.locator, workspace_hint):
                    return resource.locator
        for resource in resources:
            if resource.role == "target_mutable" and resource.locator:
                return resource.locator
        return resources[0].locator if resources else workspace_hint

    def _resource(
        self,
        *,
        path: str,
        role: str,
        kind: str,
        graph: dict[str, Any],
        evidence: str,
        confidence: float,
    ) -> MissionResourceScope:
        if role not in {"source_readonly", "target_mutable"}:
            role = "source_readonly"
        permissions = set(self.READ_PERMISSIONS)
        if role == "target_mutable" and graph.get("mutation_intent"):
            permissions.update(self.MUTATION_PERMISSIONS)
        requested_effects = {str(item) for item in graph.get("requested_effects", []) or []}
        if role == "target_mutable" and (
            graph.get("execution_intent")
            or requested_effects.intersection({"build_execution", "test_execution", "runtime_execution"})
        ):
            permissions.update(self.EXECUTION_PERMISSIONS)
        digest = hashlib.sha256(
            f"{self._normalize_path(path)}|{role}".encode("utf-8")
        ).hexdigest()[:16]
        return MissionResourceScope(
            resource_id=f"local_workspace_{digest}",
            resource_type="local_workspace",
            role=role,
            locator=path,
            permissions=sorted(permissions),
            provenance_refs=[evidence],
            metadata={
                "kind": kind,
                "confidence": round(confidence, 3),
                "source": "prompt_semantic_ingress",
            },
        )

    def _fallback_role(
        self,
        *,
        path: str,
        kind: str,
        workspace_hint: str | None,
        graph: dict[str, Any],
    ) -> str:
        if kind == "library":
            return "source_readonly"
        if workspace_hint and self._same_path(path, workspace_hint):
            return "target_mutable" if graph.get("mutation_intent") else "source_readonly"
        if graph.get("readonly_contract"):
            return "source_readonly"
        return "target_mutable" if graph.get("mutation_intent") else "source_readonly"

    def _kind(self, prompt: str, path: str) -> str:
        prompt_fold = prompt.casefold()
        index = prompt_fold.find(path.casefold())
        before = prompt[max(0, index - 240):index] if index >= 0 else ""
        normalized = self._normalize_text(before)
        library_terms = (
            "corpus",
            "biblioteca",
            "library",
            "dataset",
            "media corpus",
            "corpus de testes",
            "biblioteca de testes",
        )
        return "library" if any(term in normalized for term in library_terms) else "project"

    def _graph(self, value: dict[str, Any] | Any | None) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return dict(value.model_dump(mode="json"))
        return {}

    def _normalize_text(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))

    def _normalize_path(self, value: str) -> str:
        return os.path.normcase(str(Path(value).expanduser().resolve(strict=False)))

    def _same_path(self, left: str, right: str) -> bool:
        return self._normalize_path(left) == self._normalize_path(right)
