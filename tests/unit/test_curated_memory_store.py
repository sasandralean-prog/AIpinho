from aipinho.schemas.memory.curated_memory import CuratedMemoryEvent
from aipinho.services.memory.curated_memory_store import CuratedMemoryStore
from tests.unit.curated_memory_test_helpers import approved_candidate_flow


def test_curated_memory_store_saves_memory_versions_trace_and_events(tmp_path):
    _, _, result, *_ = approved_candidate_flow(tmp_path)
    store = CuratedMemoryStore(root=tmp_path / "curated")
    assert result.memory is not None
    assert store.get_memory(result.memory.memory_id).memory_id == result.memory.memory_id
    assert store.get_versions(result.memory.memory_id)[0].version == 1
    assert store.get_trace(result.memory.memory_id)
    store.append_event(result.memory.memory_id, "unit_event", "ok", "stored")
    assert any(event.event_type == "unit_event" for event in store.get_events(result.memory.memory_id))


def test_curated_memory_store_redacts_secret_like_event_metadata(tmp_path):
    _, _, result, _, _, store, *_ = approved_candidate_flow(tmp_path)
    store.append_event(result.memory.memory_id, "secret_event", "ok", "stored", {"token": "abcdef123456"})
    assert "abcdef123456" not in str(store.get_events(result.memory.memory_id))
