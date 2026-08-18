from aipinho.schemas.prompts.prompt_context_item import PromptContextItem
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.services.prompts.prompt_budget_service import PromptBudgetService


def test_prompt_budget_estimates_and_summarizes_usage():
    service = PromptBudgetService()
    budget = service.budget_for("chat")
    assert budget.max_input_chars > 0
    result = service.summarize_budget(
        [PromptMessage(role="user", content="abcd")],
        [PromptContextItem(source_type="metadata", title="m", content="efgh", priority=0.1)],
        budget,
    )
    assert result.used_input_chars == 8
    assert result.estimated_tokens == 2
