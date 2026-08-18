from aipinho.services.rag.integration.memory_context_selector import MemoryContextSelector
from tests.unit.rag_memory_test_helpers import memory


def test_explicit_active_memory_selected():
    selection = MemoryContextSelector().select([memory()], explicit=True)
    assert len(selection.items) == 1
    assert selection.items[0].kind == "curated_memory"


def test_candidate_and_expired_memory_blocked():
    selection = MemoryContextSelector().select([memory(status="candidate"), memory(status="expired")], explicit=True)
    assert not selection.items
    assert len(selection.blocked_items) == 2


def test_scope_match_and_max_items():
    memories = [memory(memory_id=f"m{i}", workspace="A") for i in range(6)]
    selection = MemoryContextSelector().select(memories, explicit=True, workspace="A", max_items=4)
    assert len(selection.items) == 4
    mismatch = MemoryContextSelector().select([memory(workspace="B")], explicit=True, workspace="A")
    assert mismatch.blocked_items[0]["reason"] == "memory_scope_mismatch"

