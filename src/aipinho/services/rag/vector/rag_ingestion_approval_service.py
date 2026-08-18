from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService


class RAGIngestionApprovalService:
    def __init__(self, preview_service: RAGIngestionPreviewService | None = None) -> None:
        self.preview_service = preview_service or RAGIngestionPreviewService()
        self.store_dir = PATHS.project_root / "data" / "runtime" / "rag_ingestions" / "approvals"

    def create_approval(self, preview_id: str, *, reason: str = "") -> dict[str, object]:
        stored = self.preview_service.get_preview(preview_id)
        if not stored:
            return {"status": "blocked", "blocked_reasons": ["preview_not_found"]}
        preview = stored["preview"]
        if preview.get("status") != "ready":
            return {"status": "blocked", "blocked_reasons": ["preview_not_ready"]}
        approval = {
            "approval_id": f"rag_approval_{uuid4().hex}",
            "preview_id": preview_id,
            "status": "pending",
            "scope": "vector_rag_ingestion",
            "reason": reason,
            "execution_status": "not_executed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save(approval)
        return {"status": "ok", "approval": approval, "ingested": False}

    def approve(self, approval_id: str) -> dict[str, object]:
        approval = self.get_approval(approval_id)
        if not approval:
            return {"status": "blocked", "blocked_reasons": ["approval_not_found"]}
        if approval["status"] != "pending":
            return {"status": "blocked", "blocked_reasons": ["approval_not_pending"]}
        approval["status"] = "approved"
        approval["execution_status"] = "not_executed"
        approval["decided_at"] = datetime.now(timezone.utc).isoformat()
        self._save(approval)
        return {"status": "ok", "approval": approval, "ingested": False}

    def get_approval(self, approval_id: str) -> dict | None:
        path = self.store_dir / f"{approval_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, approval: dict) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        (self.store_dir / f"{approval['approval_id']}.json").write_text(json.dumps(approval, indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_ingestion_approval", "approval_does_not_execute": True}
