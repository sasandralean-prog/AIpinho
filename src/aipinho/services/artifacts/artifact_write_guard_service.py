from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_write_guard import ArtifactWriteGuard
from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_content_validator import ArtifactContentValidator
from aipinho.services.artifacts.artifact_overwrite_policy_service import ArtifactOverwritePolicyService
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore
from aipinho.services.artifacts.artifact_risk_service import ArtifactRiskService
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactWriteGuardService:
    def __init__(self, preview_store: ArtifactPreviewStore | None = None, approval_store: ApprovalStore | None = None) -> None:
        self.preview_store = preview_store or ArtifactPreviewStore()
        self.approval_store = approval_store or ApprovalStore()
        self.path_guard = ArtifactPathGuardService()
        self.content_validator = ArtifactContentValidator()
        self.risk_service = ArtifactRiskService()
        self.overwrite_policy = ArtifactOverwritePolicyService()
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_write_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")

    def validate(self, request: ArtifactWriteRequest) -> ArtifactWriteGuard:
        blocked: list[str] = []
        warnings: list[str] = []
        trace: list[str] = ["artifact_write_guard_started"]
        if not request.operator_confirmed:
            blocked.append("operator_confirmation_required")
        preview = self.preview_store.get_preview(request.preview_id)
        if preview is None:
            blocked.append("artifact_preview_not_found")
            return ArtifactWriteGuard(allowed=False, preview_id=request.preview_id, approval_id=request.approval_id, blocked_reasons=blocked, trace=trace)
        approval = self.approval_store.get(request.approval_id) if request.approval_id else None
        if approval is None:
            blocked.append("approval_missing")
        else:
            if approval.preview_id != preview.preview_id:
                blocked.append("approval_preview_mismatch")
            if approval.status != "approved":
                blocked.append(f"approval_{approval.status}")
            if approval.approval_scope not in {"future_artifact_write", "artifact_write_execute"}:
                blocked.append("approval_scope_invalid")
            if approval.execution_status != "not_executed":
                blocked.append("approval_already_executed_or_invalid")
            if self._expired(approval.expires_at):
                blocked.append("approval_expired")
            trace_hash = getattr(approval.policy_snapshot, "trace_hash", "")
            if trace_hash and trace_hash != preview.content_hash:
                blocked.append("approval_hash_mismatch")
        if preview.status != "approved_for_future_write":
            blocked.append("preview_not_approved")
        if preview.approval_id and preview.approval_id != request.approval_id:
            blocked.append("preview_approval_mismatch")
        if not preview.validation.valid or preview.risk.blocked:
            blocked.append("preview_invalid_or_blocked")
        if preview.risk.risk_level == "critical":
            blocked.append("critical_risk")
        target_validation = self.path_guard.validate(preview.workspace, preview.target.target_path)
        if not target_validation.valid or target_validation.target is None:
            blocked.extend(target_validation.blocked_reasons)
        if target_validation.target and preview.target.normalized_target_path and target_validation.target.normalized_target_path != preview.target.normalized_target_path:
            blocked.append("target_mismatch")
        content = preview.content_preview
        content_validation = self.content_validator.validate(content, fmt=preview.source.format, artifact_type=preview.artifact_type)
        if not content_validation.valid:
            blocked.extend(content_validation.blocked_reasons)
        if content_validation.content_hash != preview.content_hash:
            blocked.append("content_hash_mismatch")
        risk = self.risk_service.assess(target_validation, content_validation)
        if risk.blocked or risk.risk_level == "critical":
            blocked.extend(risk.reasons or ["risk_revalidation_failed"])
        target_path = target_validation.target.normalized_target_path if target_validation.target else preview.target.normalized_target_path
        existing_hash = self._file_hash(Path(target_path)) if target_path and Path(target_path).exists() else None
        overwrite_blocked, overwrite_warnings = self.overwrite_policy.validate(preview, allow_overwrite=request.allow_overwrite, current_existing_hash=existing_hash)
        blocked.extend(overwrite_blocked)
        warnings.extend([*target_validation.warnings, *content_validation.warnings, *risk.warnings, *overwrite_warnings])
        unique_blocked = list(dict.fromkeys(blocked))
        allowed = not unique_blocked
        trace.append("artifact_write_guard_allowed" if allowed else "artifact_write_guard_blocked")
        return ArtifactWriteGuard(
            allowed=allowed,
            status="ready_to_execute" if allowed else "blocked",
            preview_id=preview.preview_id,
            approval_id=request.approval_id,
            target_path=target_path,
            content_hash=preview.content_hash,
            resolved_content=content if allowed else "",
            would_overwrite=preview.would_overwrite,
            existing_hash=existing_hash,
            blocked_reasons=unique_blocked,
            warnings=list(dict.fromkeys(warnings)),
            trace=trace,
        )

    def _expired(self, value: str) -> bool:
        try:
            expires = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return expires < datetime.now(timezone.utc)
        except Exception:
            return True

    def _file_hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_write_guard", "requires_preview_approval_hash_target_lock": True}
