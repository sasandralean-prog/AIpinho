from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextBudgetResult, ContextInjectionItem
from aipinho.services.rag.integration.config import integration_config


class ContextBudgetCoordinator:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or integration_config("context_budget_policy.yaml")

    def apply(self, items: list[ContextInjectionItem], overrides: dict | None = None) -> tuple[list[ContextInjectionItem], ContextBudgetResult]:
        limits = dict(self.config.get("budget") or {})
        limits.update(overrides or {})
        max_total = int(limits.get("max_context_items_total", 12))
        max_retrieval = int(limits.get("max_retrieval_items", 8))
        max_memory = int(limits.get("max_memory_items", 4))
        max_chars = int(limits.get("max_context_chars_total", 24000))
        max_per_item = int(limits.get("max_context_chars_per_item", 2500))
        selected: list[ContextInjectionItem] = []
        omitted: list[str] = []
        truncated: list[str] = []
        used = 0
        retrieval_count = 0
        memory_count = 0
        for original in sorted(items, key=self._priority):
            item = original.model_copy(deep=True)
            is_memory = item.kind == "curated_memory"
            if len(selected) >= max_total or (is_memory and memory_count >= max_memory) or (not is_memory and retrieval_count >= max_retrieval):
                omitted.append(item.context_item_id)
                continue
            content = item.content
            if len(content) > max_per_item:
                content = content[:max_per_item]
                item.content = content
                item.truncated = True
                item.warnings.append("context_item_truncated")
                truncated.append(item.context_item_id)
            if used + len(content) > max_chars:
                remaining = max_chars - used
                if remaining <= 0:
                    omitted.append(item.context_item_id)
                    continue
                item.content = content[:remaining]
                item.truncated = True
                item.warnings.append("context_item_truncated")
                truncated.append(item.context_item_id)
            selected.append(item)
            used += len(item.content)
            if is_memory:
                memory_count += 1
            else:
                retrieval_count += 1
        warnings = []
        if omitted:
            warnings.append("context_items_omitted_by_budget")
        if truncated:
            warnings.append("context_items_truncated_by_budget")
        status = "partial" if warnings else "fit"
        return selected, ContextBudgetResult(
            status=status,
            max_items=max_total,
            max_chars=max_chars,
            input_items=len(items),
            admitted_items=len(selected),
            retrieval_items=retrieval_count,
            memory_items=memory_count,
            used_chars=used,
            omitted_item_ids=omitted,
            truncated_item_ids=list(dict.fromkeys(truncated)),
            warnings=warnings,
        )

    def _priority(self, item: ContextInjectionItem) -> tuple[float, int, str]:
        kind_weight = {
            "evidence_item": 80,
            "report_section": 70,
            "curated_memory": 60,
            "file_excerpt": 55,
            "retrieval_hit": 50,
        }.get(item.kind, 0)
        return (-float(kind_weight + item.score), item.rank, item.context_item_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_budget_coordinator", "shared_budget": True}
