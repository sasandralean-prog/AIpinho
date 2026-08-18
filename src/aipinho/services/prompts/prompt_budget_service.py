from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.prompts.prompt_budget import PromptBudget
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.utils.yaml_loader import load_yaml_file


class PromptBudgetService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "prompts" / "prompt_budgets.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def budget_for(self, purpose: str) -> PromptBudget:
        budgets = self.config.get("budgets", {}) if isinstance(self.config.get("budgets", {}), dict) else {}
        value = budgets.get(purpose) or budgets.get("default", {})
        return PromptBudget(max_input_chars=int(value.get("max_input_chars", 20000)), max_context_items=int(value.get("max_context_items", 20)), max_chars_per_context_item=int(value.get("max_chars_per_context_item", 4000)), max_output_tokens=int(value.get("max_output_tokens", 512)))

    def estimate_chars(self, messages: list[PromptMessage] | None = None, context_items: list[PromptContextItem] | None = None) -> int:
        return sum(len(item.content) for item in messages or []) + sum(len(item.content) for item in context_items or [])

    def estimate_tokens_rough(self, chars: int) -> int:
        return max(1, (chars + 3) // 4) if chars > 0 else 0

    def summarize_budget(self, messages: list[PromptMessage], context_items: list[PromptContextItem], budget: PromptBudget) -> PromptBudget:
        used = self.estimate_chars(messages, context_items)
        budget.used_input_chars = used
        budget.estimated_tokens = self.estimate_tokens_rough(used)
        return budget

    def status(self) -> dict[str, object]:
        budgets = self.config.get("budgets", {}) if isinstance(self.config.get("budgets", {}), dict) else {}
        return {"status": "ok", "service": "prompt_budget", "budgets": sorted(budgets.keys())}
