from __future__ import annotations


class ApprovalTrace:
    def item(self, *, stage: str, decision: str, reason: str, source: str) -> dict[str, object]:
        return {"stage": stage, "decision": decision, "reason": reason, "source": source}