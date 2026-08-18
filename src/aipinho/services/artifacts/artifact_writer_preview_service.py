from __future__ import annotations

from uuid import uuid4
from pathlib import Path
import hashlib

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_draft import ArtifactDraftRequest
from aipinho.schemas.artifacts.artifact_preview import ArtifactPreview, ArtifactPreviewRequest
from aipinho.schemas.artifacts.artifact_status import ArtifactWriterStatus
from aipinho.schemas.artifacts.artifact_validation import ArtifactValidation
from aipinho.services.artifacts.artifact_content_validator import ArtifactContentValidator
from aipinho.services.artifacts.artifact_diff_preview_service import ArtifactDiffPreviewService
from aipinho.services.artifacts.artifact_draft_service import ArtifactDraftService
from aipinho.services.artifacts.artifact_format_validator import ArtifactFormatValidator
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore
from aipinho.services.artifacts.artifact_risk_service import ArtifactRiskService
from aipinho.services.artifacts.artifact_source_resolver import ArtifactSourceResolver
from aipinho.services.artifacts.artifact_target_policy_service import ArtifactTargetPolicyService
from aipinho.services.artifacts.artifact_trace_service import ArtifactTraceService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file


class ArtifactWriterPreviewService:
    CONFIGS = [
        "artifact_writer_policy.yaml",
        "artifact_target_policy.yaml",
        "artifact_content_policy.yaml",
        "artifact_format_policy.yaml",
        "artifact_preview_policy.yaml",
        "artifact_risk_policy.yaml",
        "artifact_approval_policy.yaml",
        "artifact_store_policy.yaml",
        "artifact_diff_policy.yaml",
        "artifact_source_policy.yaml",
    ]

    def __init__(self, store: ArtifactPreviewStore | None = None, target_policy: ArtifactTargetPolicyService | None = None) -> None:
        self.store = store or ArtifactPreviewStore()
        self.writer_policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_writer_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        self.target_policy = target_policy or ArtifactTargetPolicyService()
        self.path_guard = ArtifactPathGuardService(self.target_policy)
        self.content_validator = ArtifactContentValidator()
        self.format_validator = ArtifactFormatValidator()
        self.risk_service = ArtifactRiskService()
        self.diff_service = ArtifactDiffPreviewService()
        self.source_resolver = ArtifactSourceResolver()
        self.draft_service = ArtifactDraftService(self.store)
        self.trace = ArtifactTraceService()

    def create_draft(self, request: ArtifactDraftRequest):
        return self.draft_service.create_draft(request)

    def get_draft(self, draft_id: str):
        return self.draft_service.get_draft(draft_id)

    def create_preview(self, request: ArtifactPreviewRequest | ArtifactDraftRequest) -> ArtifactPreview:
        draft = None
        if isinstance(request, ArtifactPreviewRequest) and request.draft_id:
            draft = self.store.get_draft(request.draft_id)
            if draft is None:
                raise ValueError("artifact_draft_not_found")
        else:
            draft = self.draft_service.create_draft(ArtifactDraftRequest(**request.model_dump(exclude={"draft_id"})))
        source_result = self.source_resolver.resolve(request.source)
        fmt = self.format_validator.detect_format(request.target_path)
        if request.source.format != "unknown":
            fmt = request.source.format
        target_validation = self.path_guard.validate(request.workspace, request.target_path)
        content_validation = self.content_validator.validate(source_result.content, fmt=fmt, artifact_type=request.artifact_type)
        blocked = [*source_result.blocked_reasons, *target_validation.blocked_reasons, *content_validation.blocked_reasons]
        validation = ArtifactValidation(
            valid=not blocked,
            target=target_validation,
            content=content_validation,
            validation_gate_summary=source_result.validation_summary,
            blocked_reasons=list(dict.fromkeys(blocked)),
            warnings=list(dict.fromkeys([*source_result.warnings, *target_validation.warnings, *content_validation.warnings])),
        )
        risk = self.risk_service.assess(target_validation, content_validation)
        diff = self.diff_service.preview(target_validation, source_result.content) if target_validation.target else None
        status = "blocked" if blocked or risk.blocked or not risk.preview_allowed else "needs_approval"
        max_preview = int((load_yaml_file(PATHS.config_root / "artifacts" / "artifact_preview_policy.yaml", critical=True, root=PATHS.config_root / "artifacts").get("preview", {}) or {}).get("max_preview_chars", 20000))
        now = utc_now()
        trace = [self.trace.item("artifact_writer_preview", "started", "preview_only_flow", source="services/artifacts/artifact_writer_preview_service.py")]
        source_trace = source_result.source.metadata.get("trace")
        if isinstance(source_trace, list):
            trace.extend(source_trace)
        trace.extend(target_validation.trace)
        trace.extend(content_validation.trace)
        trace.extend(risk.trace)
        trace.append(self.trace.item("artifact_writer_preview", status, "preview_created_without_workspace_write", source="services/artifacts/artifact_writer_preview_service.py", data={"write_allowed_now": False, "safe_to_execute": False}))
        metadata = dict(request.metadata)
        if target_validation.would_overwrite and target_validation.target and target_validation.target.normalized_target_path:
            target_path = Path(target_validation.target.normalized_target_path)
            if target_path.exists() and target_path.is_file():
                try:
                    metadata["existing_target_hash"] = hashlib.sha256(target_path.read_bytes()).hexdigest()
                    metadata["existing_target_size_bytes"] = target_path.stat().st_size
                except Exception:
                    metadata["existing_target_snapshot_warning"] = "existing_target_snapshot_unavailable"
        preview = ArtifactPreview(
            preview_id=f"artifact_preview_{uuid4().hex}",
            draft_id=draft.draft_id if draft else None,
            status=status,  # type: ignore[arg-type]
            workspace=request.workspace,
            target=target_validation.target,
            source=request.source,
            artifact_type=request.artifact_type,
            title=request.title,
            content_preview=content_validation.redacted_preview[:max_preview],
            content_hash=content_validation.content_hash,
            validation=validation,
            risk=risk,
            diff=diff,
            approval_required=risk.approval_required and status != "blocked",
            write_allowed_now=False,
            safe_to_execute=False,
            would_write=True,
            would_overwrite=target_validation.would_overwrite,
            created_at=now,
            updated_at=now,
            warnings=list(dict.fromkeys([*validation.warnings, *risk.warnings])),
            blocked_reasons=list(dict.fromkeys([*blocked, *risk.reasons])) if status == "blocked" else [],
            metadata=metadata,
            trace=trace,
        )
        return self.store.save_preview(preview)

    def refresh_validation(self, preview_id: str) -> ArtifactPreview:
        existing = self.get_preview(preview_id)
        if existing is None:
            raise ValueError("artifact_preview_not_found")
        request = ArtifactPreviewRequest(
            draft_id=existing.draft_id,
            workspace=existing.workspace,
            target_path=existing.target.target_path,
            source=existing.source,
            artifact_type=existing.artifact_type,
            title=existing.title,
            metadata=existing.metadata,
        )
        refreshed = self.create_preview(request)
        refreshed.preview_id = existing.preview_id
        refreshed.approval_id = existing.approval_id
        refreshed.approval_status = existing.approval_status
        refreshed.created_at = existing.created_at
        return self.store.save_preview(refreshed)

    def get_preview(self, preview_id: str) -> ArtifactPreview | None:
        return self.store.get_preview(preview_id)

    def list_previews(self, **filters):
        return self.store.list_previews(**filters)

    def get_diff(self, preview_id: str):
        preview = self.get_preview(preview_id)
        return preview.diff if preview else None

    def get_trace(self, preview_id: str):
        return self.store.get_trace(preview_id)

    def status(self) -> ArtifactWriterStatus:
        statuses = [inspect_yaml_file(PATHS.config_root / "artifacts" / name, root=PATHS.config_root / "artifacts") for name in self.CONFIGS]
        warnings = [f"{status.path}:{status.status}" for status in statuses if status.status != "ok"]
        settings = self.writer_policy.get("artifact_writer", {}) if isinstance(self.writer_policy.get("artifact_writer"), dict) else {}
        return ArtifactWriterStatus(
            status="degraded" if warnings else "ok",
            enabled=bool(settings.get("enabled", True)),
            mode=str(settings.get("mode", "preview_only")),
            write_enabled=bool(settings.get("write_enabled", False)),
            overwrite_execution_enabled=False,
            source_code_targets_blocked=True,
            approval_required_for_future_write=bool(settings.get("require_approval_for_future_write", True)),
            allowed_extensions=self.target_policy.allowed_extensions(),
            blocked_extensions=self.target_policy.blocked_extensions(),
            allowed_base_dirs=self.target_policy.allowed_base_dirs(),
            warnings=warnings,
        )
