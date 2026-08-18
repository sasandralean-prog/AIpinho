from aipinho.repositories.maintenance.invariant_repository import InvariantRepository
from aipinho.schemas.maintenance.contracts import InvariantCheckRequest
from aipinho.services.maintenance.invariant_checker import InvariantChecker
from tests.maintenance_helpers import NullEmitter

def test_generic_rule_evaluator_detects_patch_readonly(tmp_path):
    emitter = NullEmitter()
    checker = InvariantChecker(repository=InvariantRepository(tmp_path / "invariants"), emitter=emitter)
    result = checker.check(InvariantCheckRequest(signals={"requires_patch": True, "read_only": True}))
    assert result.violations[0].invariant_id == "patch_never_with_read_only"
    assert result.violations[0].severity == "critical"
