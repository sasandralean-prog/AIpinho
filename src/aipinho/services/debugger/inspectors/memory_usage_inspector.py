from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.memory.curated_memory_service import CuratedMemoryService


class MemoryUsageInspector(BaseInspector):
    target_type = "memory_usage"

    def inspect(self, memory_id: str):
        memory = CuratedMemoryService().get(memory_id)
        if memory is None:
            return self.missing(memory_id)
        data = memory.model_dump() if hasattr(memory, "model_dump") else memory
        findings = []
        status = str(data.get("status") or "") if isinstance(data, dict) else ""
        if status in {"expired", "superseded", "rejected", "archived"}:
            findings.append(finding("inactive_memory_used", f"Memory status is {status}"))
        if isinstance(data, dict) and not data.get("evidence"):
            findings.append(finding("memory_missing_evidence", "Curated memory has no evidence", "high"))
        return self.result(memory_id, {"memory": data}, findings, summary="Memory usage inspected")
