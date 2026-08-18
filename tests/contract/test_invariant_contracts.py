import pytest
from aipinho.repositories.maintenance.invariant_repository import InvariantRepository
from aipinho.schemas.maintenance.contracts import InvariantCheckRequest
from aipinho.services.maintenance.invariant_checker import InvariantChecker
from tests.maintenance_helpers import NullEmitter

CASES = [
    ({"requires_patch": True, "read_only": True}, "patch_never_with_read_only", "critical"),
    ({"apply_requested": True, "write_forbidden": True}, "write_forbidden_blocks_apply", "critical"),
    ({"unknown_event_used_by_speaker": True}, "unknown_event_not_speaker_source", "high"),
    ({"speaker_claims_operation_completed": True, "completion_event_present": False}, "speaker_no_false_progress", "critical"),
    ({"context_item_missing_source_ref": True}, "context_requires_source_ref", "high"),
    ({"rag_context_missing_citation": True}, "rag_requires_citation", "high"),
    ({"expired_or_superseded_memory_active": True}, "expired_memory_not_active", "high"),
    ({"skill_expands_contract": True}, "skill_cannot_expand_contract", "critical"),
    ({"tool_outside_skill_allowlist": True}, "tool_not_allowed_by_skill_blocked", "critical"),
    ({"model_14b_auto_selected": True}, "fourteen_b_manual_only", "critical"),
    ({"raw_log_promoted_to_memory": True}, "raw_log_not_memory", "high"),
    ({"debugger_mutation_requested": True}, "debugger_read_only", "critical"),
    ({"supervisor_self_restart_requested": True}, "monitor_9099_not_self_restart", "critical"),
    ({"mobile_launcher_direct_sync": True}, "mobile_not_direct_launcher_sync", "medium"),
    ({"external_connector_default_enabled": True}, "external_connector_disabled_by_default", "high"),
]

@pytest.mark.parametrize("signals,invariant_id,severity", CASES)
def test_registered_invariant_cases(signals, invariant_id, severity, tmp_path):
    checker = InvariantChecker(repository=InvariantRepository(tmp_path / invariant_id), emitter=NullEmitter())
    result = checker.check(InvariantCheckRequest(signals=signals))
    violation = next(item for item in result.violations if item.invariant_id == invariant_id)
    assert violation.severity == severity
