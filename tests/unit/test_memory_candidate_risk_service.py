from aipinho.schemas.memory.memory_candidate import MemoryCandidateScope, MemoryCandidateSource
from aipinho.services.memory.memory_candidate_conflict_service import MemoryCandidateConflictService
from aipinho.services.memory.memory_candidate_risk_service import MemoryCandidateRiskService
from aipinho.services.memory.memory_candidate_sensitivity_scanner import SensitivityScanResult


def test_risk_critical_without_scope():
    risk = MemoryCandidateRiskService().evaluate(
        source=MemoryCandidateSource(source_type="manual_payload", source_id="x"),
        scope=MemoryCandidateScope(scope_type=""),
        evidence=[],
        sensitivity=SensitivityScanResult(status="safe"),
        conflict=MemoryCandidateConflictService().evaluate("x", kind="runtime_behavior", scope=MemoryCandidateScope(scope_type=""), existing=[]),
        kind="runtime_behavior",
    )
    assert risk.level == "critical"
