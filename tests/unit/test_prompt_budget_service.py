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


def test_prompt_budget_does_not_double_count_context_already_rendered_in_messages():
    service = PromptBudgetService()
    budget = service.budget_for("chat")
    rendered = "Context item: m\nefgh"
    result = service.summarize_budget(
        [PromptMessage(role="developer", content=rendered)],
        [PromptContextItem(source_type="metadata", title="m", content="efgh", priority=0.1)],
        budget,
        context_already_in_messages=True,
    )
    assert result.used_input_chars == len(rendered)
    assert result.estimated_tokens == service.estimate_tokens_rough(len(rendered))
