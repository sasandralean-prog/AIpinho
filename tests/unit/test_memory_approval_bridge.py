from tests.unit.curated_memory_test_helpers import candidate_request, memory_stack


def test_memory_approval_bridge_creates_curated_memory_approval_without_persisting(tmp_path):
    candidate_service, approval_service, curated_store, bridge, _ = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request()).candidate
    result = bridge.request_approval(candidate.candidate_id, reason="test")
    approval = approval_service.get_approval(result.approval_id)
    assert result.status == "pending"
    assert approval.approval_scope == "curated_memory_persist"
    assert approval.policy_snapshot.config_versions["memory"]["candidate_id"] == candidate.candidate_id
    assert curated_store.list_memories() == []


def test_memory_approval_bridge_blocks_invalid_candidate(tmp_path):
    _, _, _, bridge, _ = memory_stack(tmp_path)
    result = bridge.request_approval("missing_candidate")
    assert result.status == "blocked"
    assert "candidate_not_found" in result.blocked_reasons
