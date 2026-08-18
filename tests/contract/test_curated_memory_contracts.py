from typing import get_args

from aipinho.schemas.approvals.approval_state import ApprovalScope
from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest, MemoryApprovalRequest, MemorySearchRequest


def test_curated_memory_contracts_expose_required_requests():
    assert CuratedMemoryRequest(candidate_id="memcand_1", approval_id="approval_1", operator_confirmed=True).operator_confirmed is True
    assert MemoryApprovalRequest(candidate_id="memcand_1").candidate_id == "memcand_1"
    assert MemorySearchRequest(text="policy").text == "policy"
    assert "curated_memory_persist" in get_args(ApprovalScope)
