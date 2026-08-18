from __future__ import annotations

import json

from aipinho.schemas.vision.contracts import VisionAudit
from aipinho.services.vision.config import runtime_path


class VisionAuditService:
    def __init__(self) -> None:
        self.root = runtime_path("audit")

    def record(self, audit: VisionAudit) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{audit.audit_id}.json").write_text(json.dumps(audit.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_audit", "root": str(self.root)}
