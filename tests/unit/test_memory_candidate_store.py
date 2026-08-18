from aipinho.schemas.memory.memory_candidate import MemoryCandidateRequest
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from tests.unit.test_memory_candidate_service import valid_request


def test_store_save_get_list_events_trace_and_reject(tmp_path):
    store = MemoryCandidateStore(root=tmp_path)
    svc = MemoryCandidateService(store=store)
    candidate = svc.create_candidate(valid_request()).candidate
    loaded = store.get_candidate(candidate.candidate_id)
    assert loaded.candidate_id == candidate.candidate_id
    assert store.list_candidates(kind="policy_decision")
    assert store.get_events(candidate.candidate_id)
    assert store.get_trace(candidate.candidate_id)
    rejected = store.update_candidate_status(candidate.candidate_id, "rejected", "test")
    assert rejected.status == "rejected"


def test_store_does_not_persist_secret_plaintext(tmp_path):
    store = MemoryCandidateStore(root=tmp_path)
    svc = MemoryCandidateService(store=store)
    candidate = svc.create_candidate(MemoryCandidateRequest(text="api_key=secret12345", status="candidate")).candidate
    data = (tmp_path / f"{candidate.candidate_id}.json").read_text(encoding="utf-8")
    assert "secret12345" not in data
