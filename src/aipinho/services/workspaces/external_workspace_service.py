from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.schemas.external_workspace import (
    ExternalPathCandidate,
    WorkspaceBridgeManifest,
    WorkspaceImportPlan,
    WorkspaceImportRequest,
    WorkspaceImportResult,
    WorkspaceOnboardingRequest,
    WorkspaceOnboardingResult,
    WorkspaceRegistrationRequest,
    WorkspaceRegistrationResult,
)
from aipinho.schemas.sandbox import SandboxArtifactExportRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.projects.project_profile_detector import ProjectProfileDetector
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService
from aipinho.services.sandbox.sandbox_artifact_service import SandboxArtifactService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService
from aipinho.utils.yaml_loader import load_yaml_file


class ExternalWorkspaceService:
    DEFAULT_EXCLUDES = [
        ".git/**",
        "**/.git/**",
        ".gradle/**",
        "**/.gradle/**",
        "build/**",
        "**/build/**",
        "node_modules/**",
        "**/node_modules/**",
        ".venv/**",
        "**/.venv/**",
        "__pycache__/**",
        "**/__pycache__/**",
        "*.pyc",
        "dist/**",
        "**/dist/**",
    ]

    DEFAULT_SECRET_PATTERNS = [
        r"(?i)\bapi[_-]?key\b\s*[:=]\s*['\"]?[^'\"\s]{12,}",
        r"(?i)\bsecret\b\s*[:=]\s*['\"]?[^'\"\s]{12,}",
        r"sk-[A-Za-z0-9_\-]{16,}",
        r"AIza[0-9A-Za-z_\-]{20,}",
        r"(?i)\bpassword\b\s*[:=]\s*['\"]?[^'\"\s]{8,}",
    ]

    def __init__(
        self,
        *,
        data_root: Path | None = None,
        sandbox: SandboxWorkspaceService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        override = os.environ.get("AIPINHO_EXTERNAL_WORKSPACE_DATA_ROOT")
        self.data_root = data_root or (Path(override).expanduser().resolve() if override else PATHS.project_root / "data" / "runtime" / "external_workspaces")
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.config = config or load_yaml_file(PATHS.config_root / "workspaces" / "external_workspace_policy.yaml", critical=False, root=PATHS.config_root)
        self.sandbox = sandbox or SandboxWorkspaceService()
        self.tool_gateway = tool_gateway or AgentToolGatewayService()
        self.path_extractor = PathExtractionService()
        self.profile_detector = ProjectProfileDetector()

    def status(self) -> dict[str, object]:
        registrations = self.list_registrations()
        return {
            "status": "ok",
            "service": "external_workspace_onboarding",
            "registered_workspaces": len(registrations),
            "source_readonly": sum(1 for item in registrations if item.role == "source_readonly"),
            "target_mutable": sum(1 for item in registrations if item.role == "target_mutable"),
            "sandbox_imports": sum(1 for item in self.sandbox.list_workspaces() if item.role == "sandbox_import"),
        }

    def detect(self, *, prompt: str | None = None, path: str | None = None) -> list[ExternalPathCandidate]:
        raw_paths: list[str] = []
        if path:
            raw_paths.append(path)
        if prompt:
            raw_paths.extend(item.value for item in self.path_extractor.extract(prompt))
        candidates: list[ExternalPathCandidate] = []
        seen: set[str] = set()
        for raw in raw_paths:
            resolved = self._resolve(raw)
            key = str(resolved).casefold()
            if key in seen:
                continue
            seen.add(key)
            exists = resolved.exists()
            blocked = self._blocked_root(resolved)
            safe_actions = self._safe_actions(str(resolved), blocked=blocked)
            warnings = ["path_missing"] if not exists else []
            if blocked:
                warnings.append("external_path_blocked_by_policy")
            candidates.append(
                ExternalPathCandidate(
                    raw_path=raw,
                    resolved_path=str(resolved),
                    exists=exists,
                    is_directory=exists and resolved.is_dir(),
                    is_file=exists and resolved.is_file(),
                    status="blocked" if blocked else "candidate",
                    reason_code="external_path_blocked_by_policy" if blocked else "external_path_detected",
                    safe_actions=safe_actions,
                    warnings=warnings,
                    evidence_refs=[f"path:{resolved}"],
                )
            )
        return candidates

    def onboard(self, request: WorkspaceOnboardingRequest) -> WorkspaceOnboardingResult:
        candidates = self.detect(prompt=request.prompt, path=request.path)
        action = request.requested_action
        if action == "detect":
            return WorkspaceOnboardingResult(
                status="needs_onboarding" if candidates else "no_external_path_detected",
                requested_action=action,
                candidates=candidates,
                message="Caminho externo detectado. Escolha registrar como fonte read-only, importar para sandbox ou criar sandbox alternativo." if candidates else "Nenhum caminho externo foi detectado.",
                safe_actions=candidates[0].safe_actions if candidates else [{"action": "sandbox_alternative", "label": "Criar projeto em sandbox sem ler caminho externo"}],
                evidence_refs=[ref for candidate in candidates for ref in candidate.evidence_refs],
            )
        if action == "register":
            role = request.role or "source_readonly"
            target = request.path or (candidates[0].resolved_path if candidates else None)
            if not target:
                return WorkspaceOnboardingResult(status="blocked", requested_action=action, candidates=candidates, message="Nenhum caminho externo informado.", safe_actions=[])
            registration = self.register(WorkspaceRegistrationRequest(path=target, role=role, display_name=request.display_name))
            return WorkspaceOnboardingResult(
                status=registration.status,
                requested_action=action,
                candidates=candidates,
                registration=registration,
                message="Workspace externo registrado com papel governado.",
                safe_actions=self._registered_safe_actions(registration),
                warnings=registration.warnings,
                evidence_refs=registration.evidence_refs,
            )
        if action == "import":
            target = request.path or (candidates[0].resolved_path if candidates else None)
            if not target:
                return WorkspaceOnboardingResult(status="blocked", requested_action=action, candidates=candidates, message="Nenhum caminho externo informado.", safe_actions=[])
            plan = self.preview_import(WorkspaceImportRequest(source_path=target, target_name=request.import_target_name or request.display_name, dry_run=True))
            result = self.apply_import(plan.import_plan_id)
            return WorkspaceOnboardingResult(
                status=result.status,
                requested_action=action,
                candidates=candidates,
                import_plan=plan,
                import_result=result,
                message="Workspace externo importado para sandbox governado." if result.status == "imported" else "Importacao bloqueada ou falhou.",
                warnings=[*plan.warnings, *result.warnings],
                evidence_refs=[*plan.evidence_refs, *result.evidence_refs],
            )
        return WorkspaceOnboardingResult(status="blocked", requested_action=action, candidates=candidates, message="Acao de onboarding desconhecida.", safe_actions=[])

    def register(self, request: WorkspaceRegistrationRequest) -> WorkspaceRegistrationResult:
        root = self._resolve(request.path)
        if self._blocked_root(root):
            result = WorkspaceRegistrationResult(
                path=str(root),
                role="forbidden",
                display_name=request.display_name or root.name,
                status="blocked",
                allowed_operations=[],
                blocked_operations=["read", "write", "shell", "artifact_export"],
                reason_code="external_path_blocked_by_policy",
                warnings=["blocked_root"],
                evidence_refs=[f"path:{root}"],
            )
            return self._save_registration(result)
        if not root.exists() and not request.allow_missing:
            result = WorkspaceRegistrationResult(
                path=str(root),
                role=request.role,
                display_name=request.display_name or root.name,
                status="blocked",
                reason_code="external_path_missing",
                blocked_operations=["read", "write", "shell", "artifact_export"],
                warnings=["path_missing"],
                evidence_refs=[f"path:{root}"],
            )
            return self._save_registration(result)
        allowed, blocked = self._operations_for_role(request.role)
        candidate = self._profile_candidate(root, request.display_name)
        result = WorkspaceRegistrationResult(
            path=str(root),
            role=request.role,
            display_name=request.display_name or root.name,
            allowed_operations=allowed,
            blocked_operations=blocked,
            project_profile_candidate=candidate,
            warnings=candidate.risks if candidate else [],
            evidence_refs=[f"path:{root}", f"workspace_role:{request.role}"],
            metadata_sanitized={**request.metadata_sanitized, "reason": request.reason},
        )
        return self._save_registration(result)

    def list_registrations(self) -> list[WorkspaceRegistrationResult]:
        return [WorkspaceRegistrationResult(**json.loads(path.read_text(encoding="utf-8"))) for path in sorted(self._dir("registrations").glob("*.json"))]

    def get_registration(self, workspace_id: str) -> WorkspaceRegistrationResult:
        path = self._dir("registrations") / f"{workspace_id}.json"
        if not path.exists():
            raise FileNotFoundError(workspace_id)
        return WorkspaceRegistrationResult(**json.loads(path.read_text(encoding="utf-8")))

    def validate_access(self, workspace_id: str, operation: str) -> dict[str, object]:
        registration = self.get_registration(workspace_id)
        allowed = operation in registration.allowed_operations
        return {
            "ok": allowed,
            "workspace_id": workspace_id,
            "role": registration.role,
            "operation": operation,
            "reason_code": "workspace_operation_allowed" if allowed else "workspace_operation_denied",
            "safe_alternative": "Importe para sandbox ou registre target_mutable antes de escrever." if not allowed else None,
        }

    def preview_import(self, request: WorkspaceImportRequest) -> WorkspaceImportPlan:
        source = self._source_path(request.source_workspace_id, request.source_path)
        target_name = self._safe_name(request.target_name or source.name or "imported_workspace")
        if self._blocked_root(source) or not source.exists() or not source.is_dir():
            plan = WorkspaceImportPlan(
                source_path=str(source),
                target_name=target_name,
                status="blocked",
                warnings=["source_unavailable_or_blocked"],
                policy_decision={"allowed": False, "reason_code": "source_unavailable_or_blocked"},
                evidence_refs=[f"path:{source}"],
            )
            return self._save_plan(plan)
        files = self._collect_files(source, request.include_globs, request.exclude_globs, request.max_files, request.max_bytes)
        candidate = self._profile_candidate(source, target_name)
        plan = WorkspaceImportPlan(
            source_path=str(source),
            target_name=target_name,
            files_total=files["files_total"],
            files_included=len(files["included"]),
            files_excluded=len(files["excluded"]),
            bytes_total=files["bytes_total"],
            included_files=files["included"],
            excluded_files=files["excluded"],
            secret_findings=files["secret_findings"],
            warnings=files["warnings"],
            policy_decision={"allowed": True, "reason_code": "workspace_import_preview_allowed"},
            project_profile_candidate=candidate,
            evidence_refs=[f"path:{source}", "workspace_import_preview"],
        )
        return self._save_plan(plan)

    def apply_import(self, import_plan_id: str) -> WorkspaceImportResult:
        plan = self.get_plan(import_plan_id)
        if plan.status == "blocked":
            return self._save_import_result(
                WorkspaceImportResult(
                    import_plan_id=plan.import_plan_id,
                    status="blocked",
                    source_path=plan.source_path,
                    errors=["workspace_import_plan_blocked"],
                    evidence_refs=plan.evidence_refs,
                )
            )
        source = Path(plan.source_path).resolve(strict=False)
        workspace = self.sandbox.create_workspace(f"{plan.target_name}_{plan.import_plan_id[-8:]}", role="sandbox_import")
        target = Path(workspace.root_path_sanitized).resolve(strict=False)
        files: list[dict[str, Any]] = []
        bytes_copied = 0
        for item in plan.included_files:
            rel = str(item["relative_path"])
            src = source / rel
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            size = dst.stat().st_size
            bytes_copied += size
            files.append({"relative_path": rel, "size": size, "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()})
        manifest = WorkspaceBridgeManifest(
            source_path=str(source),
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            sandbox_root_path=str(target),
            files=files,
            secret_findings=plan.secret_findings,
            project_profile_candidate_id=plan.project_profile_candidate.candidate_id if plan.project_profile_candidate else None,
            evidence_refs=[*plan.evidence_refs, f"sandbox_workspace:{workspace.sandbox_workspace_id}"],
        )
        (target / "WORKSPACE_BRIDGE_MANIFEST.json").write_text(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        export = SandboxArtifactService().export_zip(
            SandboxArtifactExportRequest(
                sandbox_workspace_id=workspace.sandbox_workspace_id,
                filename=f"{plan.target_name}.zip",
                include_paths=["."],
            )
        )
        result = WorkspaceImportResult(
            import_plan_id=plan.import_plan_id,
            status="imported" if export.status == "ready" else "failed",
            source_path=str(source),
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            sandbox_root_path=str(target),
            manifest=manifest,
            files_copied=len(files),
            bytes_copied=bytes_copied,
            artifact_id=export.artifact_id,
            download_endpoint=export.download_endpoint,
            requires_token=export.requires_token,
            validation_status="passed" if export.status == "ready" else "failed",
            warnings=plan.warnings,
            evidence_refs=[*manifest.evidence_refs, *export.evidence_refs],
        )
        return self._save_import_result(result)

    def get_plan(self, import_plan_id: str) -> WorkspaceImportPlan:
        path = self._dir("import_plans") / f"{import_plan_id}.json"
        if not path.exists():
            raise FileNotFoundError(import_plan_id)
        return WorkspaceImportPlan(**json.loads(path.read_text(encoding="utf-8")))

    def export_registered_source(self, workspace_id: str, *, filename: str | None = None) -> WorkspaceImportResult:
        registration = self.get_registration(workspace_id)
        if registration.role != "source_readonly":
            raise PermissionError("source_readonly_required_for_export")
        plan = self.preview_import(WorkspaceImportRequest(source_workspace_id=workspace_id, target_name=filename or registration.display_name, dry_run=True))
        if plan.status == "blocked":
            return WorkspaceImportResult(import_plan_id=plan.import_plan_id, status="blocked", source_path=plan.source_path, errors=["export_preview_blocked"])
        source = Path(plan.source_path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            tmp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for item in plan.included_files:
                    rel = str(item["relative_path"])
                    archive.write(source / rel, rel)
                archive.writestr("WORKSPACE_EXPORT_MANIFEST.json", json.dumps(plan.model_dump(), ensure_ascii=False, indent=2))
            artifact = self.tool_gateway.upload_artifact(
                agent_id="external_workspace",
                session_id=workspace_id,
                request=ArtifactUploadRequest(
                    filename=filename or f"{self._safe_name(registration.display_name or 'source_export')}.zip",
                    content_type="application/zip",
                    content=base64.b64encode(tmp_path.read_bytes()).decode("ascii"),
                    encoding="base64",
                    origin="external_workspace_export",
                    metadata_sanitized={"workspace_id": workspace_id, "requires_token": True, "status": "ready"},
                ),
            )
            return WorkspaceImportResult(
                import_plan_id=plan.import_plan_id,
                status="imported",
                source_path=plan.source_path,
                files_copied=plan.files_included,
                bytes_copied=plan.bytes_total,
                artifact_id=artifact.artifact_id,
                download_endpoint=artifact.download_endpoint,
                requires_token=artifact.requires_token,
                validation_status="passed",
                warnings=plan.warnings,
                evidence_refs=[f"artifact:{artifact.artifact_id}", *plan.evidence_refs],
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def mobile_view_model(self) -> dict[str, object]:
        registrations = self.list_registrations()
        return {
            "screen": "workspace_onboarding",
            "status": "ready",
            "title": "Workspaces externos",
            "summary": "Registre fontes read-only ou importe para sandbox antes de executar.",
            "registered_count": len(registrations),
            "cards": [
                {
                    "type": "workspace_registration",
                    "workspace_id": item.workspace_id,
                    "label": item.display_name or Path(item.path).name,
                    "role": item.role,
                    "status": item.status,
                    "allowed_operations": item.allowed_operations,
                    "blocked_operations": item.blocked_operations,
                }
                for item in registrations
            ],
            "safe_actions": [
                {"action": "detect", "label": "Detectar caminho externo"},
                {"action": "register_source_readonly", "label": "Registrar fonte read-only"},
                {"action": "import_to_sandbox", "label": "Importar para sandbox"},
            ],
        }

    def _collect_files(
        self,
        source: Path,
        include_globs: list[str],
        exclude_globs: list[str],
        max_files: int | None,
        max_bytes: int | None,
    ) -> dict[str, Any]:
        effective_excludes = [*self.DEFAULT_EXCLUDES, *self._config_list("exclude_globs"), *exclude_globs]
        max_files = int(max_files or self.config.get("max_files", 5000))
        max_bytes = int(max_bytes or self.config.get("max_bytes", 100_000_000))
        included: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        secret_findings: list[dict[str, Any]] = []
        bytes_total = 0
        warnings: list[str] = []
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source).as_posix()
            if not self._matches_any(rel, include_globs):
                excluded.append({"relative_path": rel, "reason": "not_included"})
                continue
            if self._matches_any(rel, effective_excludes):
                excluded.append({"relative_path": rel, "reason": "excluded_by_policy"})
                continue
            size = path.stat().st_size
            if len(included) >= max_files or bytes_total + size > max_bytes:
                excluded.append({"relative_path": rel, "reason": "import_limit_reached"})
                warnings.append("import_limit_reached")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            findings = self._scan_secret(path, rel)
            secret_findings.extend(findings)
            included.append({"relative_path": rel, "size": size, "sha256": digest, "secret_risk": bool(findings)})
            bytes_total += size
        return {
            "files_total": len(included) + len(excluded),
            "included": included,
            "excluded": excluded,
            "secret_findings": secret_findings,
            "bytes_total": bytes_total,
            "warnings": sorted(set(warnings + (["secret_risk_detected"] if secret_findings else []))),
        }

    def _safe_actions(self, path: str, *, blocked: bool) -> list[dict[str, Any]]:
        if blocked:
            return [{"action": "sandbox_alternative", "label": "Criar alternativa em sandbox sem ler caminho externo"}]
        return [
            {"action": "register_source_readonly", "label": "Registrar como fonte read-only", "path": path},
            {"action": "import_to_sandbox", "label": "Importar copia para sandbox", "path": path},
            {"action": "register_target_mutable", "label": "Registrar como destino mutavel governado", "path": path},
            {"action": "sandbox_alternative", "label": "Criar alternativa em sandbox sem ler caminho externo"},
        ]

    def _registered_safe_actions(self, registration: WorkspaceRegistrationResult) -> list[dict[str, Any]]:
        actions = [{"action": "validate_access", "label": "Validar acesso", "workspace_id": registration.workspace_id}]
        if registration.role == "source_readonly":
            actions.extend([
                {"action": "inventory_source", "label": "Inventariar fonte read-only", "workspace_id": registration.workspace_id},
                {"action": "import_to_sandbox", "label": "Importar fonte para sandbox", "workspace_id": registration.workspace_id},
                {"action": "export_source_artifact", "label": "Exportar fonte como artifact", "workspace_id": registration.workspace_id},
            ])
        if registration.role == "target_mutable":
            actions.append({"action": "promotion_target", "label": "Usar como destino de promocao governada", "workspace_id": registration.workspace_id})
        return actions

    def _operations_for_role(self, role: str) -> tuple[list[str], list[str]]:
        if role == "source_readonly":
            return ["read", "list", "inventory", "artifact_export", "import_to_sandbox"], ["write", "apply_patch", "shell_write", "delete"]
        if role == "target_mutable":
            return ["read", "list", "preview_write", "apply_approved_patch", "validation", "governed_shell"], ["direct_write", "delete_unapproved"]
        if role == "sandbox_import":
            return ["read", "list", "write", "validation", "artifact_export", "safe_shell"], ["write_source"]
        if role in {"protected", "forbidden"}:
            return [], ["read", "write", "shell", "artifact_export"]
        return ["read", "list"], ["write", "shell"]

    def _source_path(self, source_workspace_id: str | None, source_path: str | None) -> Path:
        if source_workspace_id:
            registration = self.get_registration(source_workspace_id)
            if registration.role not in {"source_readonly", "target_mutable"}:
                raise PermissionError("workspace_role_not_importable")
            return Path(registration.path).resolve(strict=False)
        if not source_path:
            raise ValueError("source_path_required")
        return self._resolve(source_path)

    def _profile_candidate(self, root: Path, display_name: str | None):
        try:
            return self.profile_detector.detect(str(root), display_name=display_name)
        except Exception:
            return None

    def _scan_secret(self, path: Path, rel: str) -> list[dict[str, Any]]:
        if path.stat().st_size > int(self.config.get("secret_scan_max_bytes", 200_000)):
            return []
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        findings = []
        patterns = self.config.get("secret_patterns") if isinstance(self.config.get("secret_patterns"), list) else self.DEFAULT_SECRET_PATTERNS
        for pattern in patterns:
            if re.search(str(pattern), text):
                findings.append({"relative_path": rel, "pattern": "secret_like_value", "action": "redacted_in_manifest"})
        return findings

    def _blocked_root(self, path: Path) -> bool:
        resolved = path.resolve(strict=False)
        text = str(resolved).casefold()
        blocked = [str(item).casefold() for item in self.config.get("blocked_roots", [])] if isinstance(self.config.get("blocked_roots"), list) else []
        if any(text == item or text.startswith(item.rstrip("\\/") + os.sep) for item in blocked):
            return True
        if resolved.parent == resolved:
            return True
        return False

    def _matches_any(self, rel: str, patterns: list[str]) -> bool:
        if not patterns:
            return True
        return any(pattern in {"*", "**/*"} or fnmatch.fnmatch(rel, pattern) for pattern in patterns)

    def _config_list(self, key: str) -> list[str]:
        value = self.config.get(key, [])
        return [str(item) for item in value] if isinstance(value, list) else []

    def _resolve(self, raw: str) -> Path:
        return Path(raw).expanduser().resolve(strict=False)

    def _safe_name(self, value: str) -> str:
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("._-")
        return safe or "workspace"

    def _dir(self, name: str) -> Path:
        path = self.data_root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save_registration(self, result: WorkspaceRegistrationResult) -> WorkspaceRegistrationResult:
        path = self._dir("registrations") / f"{result.workspace_id}.json"
        path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _save_plan(self, plan: WorkspaceImportPlan) -> WorkspaceImportPlan:
        path = self._dir("import_plans") / f"{plan.import_plan_id}.json"
        path.write_text(json.dumps(plan.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return plan

    def _save_import_result(self, result: WorkspaceImportResult) -> WorkspaceImportResult:
        path = self._dir("import_results") / f"{result.import_result_id}.json"
        path.write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result
