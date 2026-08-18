from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextConflict, ContextInjectionItem
from aipinho.services.rag.integration.config import integration_config


class ContextConflictDetector:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or integration_config("context_conflict_policy.yaml")

    def detect(self, items: list[ContextInjectionItem]) -> list[ContextConflict]:
        pairs = ((self.config.get("patterns") or {}).get("pairs") or [])
        conflicts: list[ContextConflict] = []
        for left_index, left in enumerate(items):
            left_text = left.content.lower()
            for right in items[left_index + 1 :]:
                right_text = right.content.lower()
                for pair in pairs:
                    if len(pair) != 2:
                        continue
                    first, second = str(pair[0]).lower(), str(pair[1]).lower()
                    contradictory = (first in left_text and second in right_text) or (second in left_text and first in right_text)
                    if contradictory:
                        cross_kind = left.kind != right.kind
                        conflicts.append(
                            ContextConflict(
                                severity="high" if cross_kind and "curated_memory" in {left.kind, right.kind} else "medium",
                                item_ids=[left.context_item_id, right.context_item_id],
                                pattern=f"{first}_vs_{second}",
                                reason="contradictory_context_signals",
                            )
                        )
        return conflicts

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_conflict_detector", "deterministic": True}
