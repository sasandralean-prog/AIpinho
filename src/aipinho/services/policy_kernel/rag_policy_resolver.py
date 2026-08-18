from __future__ import annotations


class RagPolicyResolver:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "runtime_enabled": False, "reason": "Sprint 01 does not implement RAG runtime"}