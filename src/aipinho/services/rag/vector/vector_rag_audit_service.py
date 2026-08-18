from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.vector.contracts import VectorRAGAudit
from aipinho.services.rag.vector.config import rag_config


class VectorRAGAuditService:
    def __init__(self, path: Path | None = None) -> None:
        config = rag_config("rag_audit_policy.yaml")
        audit = config.get("audit", {}) if isinstance(config.get("audit", {}), dict) else {}
        self.path = path or PATHS.project_root / str(audit.get("path", "data/logs/audit/vector_rag_audit.jsonl"))

    def record(self, event: VectorRAGAudit) -> VectorRAGAudit:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.open("a", encoding="utf-8").write(json.dumps(event.model_dump(), ensure_ascii=True, sort_keys=True) + "\n")
        return event

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vector_rag_audit", "path": str(self.path)}
