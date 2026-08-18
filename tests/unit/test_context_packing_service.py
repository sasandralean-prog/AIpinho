from aipinho.schemas.prompts.prompt_budget import PromptBudget
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem, PromptContextSafety
from aipinho.services.prompts.context_packing_service import ContextPackingService


def test_context_packing_truncates_and_omits_secret_context():
    items = [
        PromptContextItem(source_type="file", title="secret", content="sk-test", priority=1, safety=PromptContextSafety(contains_secret=True)),
        PromptContextItem(source_type="file", title="long", content="x" * 100, priority=0.5),
    ]
    packed, budget, warnings = ContextPackingService().pack(items, PromptBudget(max_input_chars=50, max_context_items=2, max_chars_per_context_item=10))
    assert len(packed) == 1
    assert packed[0].content == "x" * 10
    assert budget.truncated is True
    assert any("blocked_or_secret" in item for item in budget.omitted_items)
    assert "context_item_omitted_blocked_or_secret" in warnings
