from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.artifacts.artifact_draft import ArtifactDraft, ArtifactDraftRequest
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore
from aipinho.services.artifacts.artifact_trace_service import ArtifactTraceService
from aipinho.services.session.session_store import utc_now


class ArtifactDraftService:
    def __init__(self, store: ArtifactPreviewStore | None = None) -> None:
        self.store = store or ArtifactPreviewStore()
        self.trace = ArtifactTraceService()

    def create_draft(self, request: ArtifactDraftRequest) -> ArtifactDraft:
        now = utc_now()
        draft = ArtifactDraft(
            draft_id=f"artifact_draft_{uuid4().hex}",
            workspace=request.workspace,
            target_path=request.target_path,
            source=request.source,
            artifact_type=request.artifact_type,
            title=request.title,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
            trace=[self.trace.item("artifact_draft", "created", "draft_created_without_workspace_write", source="services/artifacts/artifact_draft_service.py")],
        )
        if not request.target_path:
            draft.status = "blocked"
            draft.blocked_reasons.append("target_path_required")
        if not request.source.source_id and not request.source.content:
            draft.status = "blocked"
            draft.blocked_reasons.append("source_required")
        return self.store.save_draft(draft)

    def get_draft(self, draft_id: str) -> ArtifactDraft | None:
        return self.store.get_draft(draft_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_draft", "write_enabled": False}
