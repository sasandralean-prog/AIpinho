from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.prompts.prompt_budget import PromptBudget
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem
from aipinho.utils.yaml_loader import load_yaml_file


class ContextPackingService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "prompts" / "context_packing_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def pack(self, items: list[PromptContextItem], budget: PromptBudget) -> tuple[list[PromptContextItem], PromptBudget, list[str]]:
        warnings: list[str] = []
        selected: list[PromptContextItem] = []
        used = 0
        ordered = sorted(items, key=lambda item: (-item.priority, item.source_type, item.title, item.item_id))
        for item in ordered:
            if item.safety.blocked or item.safety.contains_secret:
                budget.omitted_items.append(f"{item.item_id}:blocked_or_secret")
                warnings.append("context_item_omitted_blocked_or_secret")
                continue
            if len(selected) >= budget.max_context_items:
                budget.omitted_items.append(f"{item.item_id}:max_context_items")
                continue
            content = item.content
            if len(content) > budget.max_chars_per_context_item:
                content = content[: budget.max_chars_per_context_item]
                item = item.model_copy(update={"content": content, "metadata": {**item.metadata, "truncated": True}})
                budget.truncated = True
                warnings.append("context_item_truncated")
            if used + len(content) > budget.max_input_chars and selected:
                budget.omitted_items.append(f"{item.item_id}:max_input_chars")
                budget.truncated = True
                continue
            selected.append(item)
            used += len(content)
        return selected, budget, list(dict.fromkeys(warnings))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_packing"}
