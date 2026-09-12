from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseDependencySnapshot,
)
from aipinho.services.runtime.phase_dependency_contract_registry import PhaseDependencyContractRegistry
from aipinho.services.runtime.phase_dependency_evaluation_service import PhaseDependencyEvaluationService


class _UnknownLimitationResolver:
    def resolve(self, **kwargs):
        return {
            "status": "insufficient_evidence",
            "reason_code": "PHASE_DEPENDENCY_LIMITATION_COMPATIBILITY_UNKNOWN",
            "assessments": {},
            "provenance": {},
        }


class _CompatibleLimitationResolver:
    def resolve(self, *, limitations, **kwargs):
        return {
            "status": "accepted",
            "assessments": {
                limitation: {
                    "impact": "COMPATIBLE_WITH_CONSTRAINT",
                    "constraints": [f"preserve_scope:{limitation}"],
                    "rationale": "fixture compatibility",
                }
                for limitation in limitations
            },
            "confidence": 0.93,
            "provenance": {"authority": "deterministic_semantic_gate"},
        }


def _requirements(**updates) -> DownstreamPhaseRequirements:
    values = {
        "contract_id": "generic_downstream_readonly_planning",
        "consumer_phase_id": "phase_2",
        "operation_type": "readonly_planning",
        "allowed_dependency_statuses": ["satisfied", "satisfied_with_limitations"],
        "required_downstream_uses": ["catalog_planning_with_limitations"],
        "required_use_safety": {
            "safe_for_catalog": [True],
            "safe_for_planning": [True, "true_with_limitations"],
            "safe_for_destructive_action": [False],
        },
        "prohibited_effects": ["workspace_mutation", "destructive_action"],
    }
    values.update(updates)
    return DownstreamPhaseRequirements(**values)


def _snapshot(**updates) -> PhaseDependencySnapshot:
    values = {
        "dependency_id": "dependency_phase1_phase2",
        "producer_task_run_id": "task_run_phase1",
        "producer_operation_id": "operation_phase1",
        "producer_phase_id": "phase_1",
        "upstream_result_ref": "task_run_result:task_run_phase1",
        "dependency_status": "satisfied",
        "evidence_refs": ["artifact:catalog"],
        "allowed_downstream_uses": ["catalog_planning_with_limitations"],
        "use_safety": {
            "safe_for_truth_claim": False,
            "safe_for_catalog": True,
            "safe_for_planning": "true_with_limitations",
            "safe_for_destructive_action": False,
        },
        "semantic_properties": {"semantic_identity": "inferred"},
    }
    values.update(updates)
    return PhaseDependencySnapshot(**values)


def _evaluate(requirements=None, snapshot=None):
    service = PhaseDependencyEvaluationService()
    requirements = requirements or _requirements()
    snapshot = snapshot or _snapshot()
    evaluation = service.evaluate(
        snapshot=snapshot,
        requirements=requirements,
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_operation_type=requirements.operation_type,
    )
    return service, requirements, snapshot, evaluation


def _authorize(service, requirements, snapshot, evaluation, **updates):
    values = {
        "evaluation": evaluation,
        "requirements": requirements,
        "consumer_task_run_id": "task_run_phase2",
        "consumer_operation_id": "operation_phase2",
        "consumer_operation_type": requirements.operation_type,
        "producer_task_run_id": snapshot.producer_task_run_id,
        "producer_operation_id": snapshot.producer_operation_id,
        "dependency_id": snapshot.dependency_id,
        "producer_phase_id": snapshot.producer_phase_id,
        "consumer_phase_id": requirements.consumer_phase_id,
    }
    values.update(updates)
    return service.authorize(**values)


def test_fully_satisfied_dependency_is_admitted() -> None:
    service, requirements, snapshot, evaluation = _evaluate(
        requirements=_requirements(
            allowed_dependency_statuses=["satisfied"],
            prohibited_effects=[],
        )
    )
    admission = _authorize(service, requirements, snapshot, evaluation)

    assert evaluation.decision == "ADMITTED"
    assert admission.authorized is True
    assert admission.constraints == []


def test_compatible_limitations_are_admitted_and_propagated() -> None:
    limitation = "semantic_identity_inferred"
    requirements = _requirements(
        limitation_compatibility={limitation: "COMPATIBLE_WITH_CONSTRAINT"},
    )
    snapshot = _snapshot(
        dependency_status="satisfied_with_limitations",
        limitations=[limitation],
        required_disclosures=[limitation],
        forbidden_claims=["authoritative_identity_truth"],
    )
    service, requirements, snapshot, evaluation = _evaluate(requirements, snapshot)
    admission = _authorize(service, requirements, snapshot, evaluation)

    assert evaluation.decision == "ADMITTED_WITH_CONSTRAINTS"
    assert admission.authorized is True
    assert f"disclose_limitation:{limitation}" in admission.constraints
    assert "forbid_claim:authoritative_identity_truth" in admission.constraints
    assert admission.evidence_refs == snapshot.evidence_refs


def test_partial_truth_does_not_block_phase_that_does_not_require_truth_safety() -> None:
    service, requirements, snapshot, evaluation = _evaluate()
    admission = _authorize(service, requirements, snapshot, evaluation)

    assert snapshot.use_safety["safe_for_truth_claim"] is False
    assert admission.authorized is True


def test_missing_required_observed_identity_blocks() -> None:
    requirements = _requirements(required_semantic_properties={"semantic_identity": ["observed"]})
    _service, _requirements_value, _snapshot_value, evaluation = _evaluate(requirements)

    assert evaluation.decision == "BLOCKED"
    assert "PHASE_DEPENDENCY_REQUIRED_SEMANTIC_PROPERTY_UNSATISFIED" in evaluation.reason_codes


def test_downstream_operation_mismatch_is_blocked() -> None:
    service = PhaseDependencyEvaluationService()
    requirements = _requirements()
    evaluation = service.evaluate(
        snapshot=_snapshot(),
        requirements=requirements,
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_operation_type="destructive_mutation",
    )

    assert evaluation.decision == "BLOCKED"
    assert "PHASE_DEPENDENCY_DOWNSTREAM_OPERATION_MISMATCH" in evaluation.reason_codes


def test_unknown_limitation_compatibility_fails_closed() -> None:
    snapshot = _snapshot(
        dependency_status="satisfied_with_limitations",
        limitations=["unclassified_upstream_limitation"],
    )
    service = PhaseDependencyEvaluationService(
        limitation_resolver=_UnknownLimitationResolver()
    )
    requirements = _requirements()
    evaluation = service.evaluate(
        snapshot=snapshot,
        requirements=requirements,
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_operation_type=requirements.operation_type,
    )

    assert evaluation.decision == "INSUFFICIENT_EVIDENCE"
    assert "PHASE_DEPENDENCY_LIMITATION_COMPATIBILITY_UNKNOWN" in evaluation.reason_codes


def test_semantically_compatible_unclassified_limitation_can_be_admitted_with_constraints() -> None:
    limitation = "upstream_identity_inferred_not_observed"
    snapshot = _snapshot(
        dependency_status="satisfied_with_limitations",
        limitations=[limitation],
        required_disclosures=[limitation],
    )
    service = PhaseDependencyEvaluationService(
        limitation_resolver=_CompatibleLimitationResolver()
    )
    requirements = _requirements()
    evaluation = service.evaluate(
        snapshot=snapshot,
        requirements=requirements,
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_operation_type=requirements.operation_type,
    )

    assert evaluation.decision == "ADMITTED_WITH_CONSTRAINTS"
    assessment = evaluation.limitation_assessments[0]
    assert assessment.source == "semantic_reasoner"
    assert assessment.impact == "COMPATIBLE_WITH_CONSTRAINT"
    assert f"preserve_scope:{limitation}" in evaluation.constraints
    assert f"disclose_limitation:{limitation}" in evaluation.constraints


def test_unsatisfied_dependency_is_blocked() -> None:
    _service, _requirements_value, _snapshot_value, evaluation = _evaluate(
        snapshot=_snapshot(dependency_status="unsatisfied")
    )

    assert evaluation.decision == "BLOCKED"
    assert "PHASE_DEPENDENCY_NOT_SATISFIED" in evaluation.reason_codes


def test_registry_has_no_implicit_contract() -> None:
    registry = PhaseDependencyContractRegistry()

    assert registry.resolve("phase_2", "readonly_planning") is None
    assert registry.contracts() == []


def test_admission_is_bound_to_taskrun_dependency_phase_and_evidence() -> None:
    service, requirements, snapshot, evaluation = _evaluate()
    admission = _authorize(service, requirements, snapshot, evaluation)

    valid, reason = service.validate_admission(
        admission,
        evaluation=evaluation,
        requirements=requirements,
        consumer_task_run_id="task_run_other",
        consumer_operation_id="operation_phase2",
        consumer_operation_type=requirements.operation_type,
        producer_task_run_id=snapshot.producer_task_run_id,
        producer_operation_id=snapshot.producer_operation_id,
        dependency_id=snapshot.dependency_id,
        producer_phase_id=snapshot.producer_phase_id,
        consumer_phase_id=requirements.consumer_phase_id,
    )

    assert valid is False
    assert reason == "PHASE_DEPENDENCY_ADMISSION_BINDING_MISMATCH"
    assert admission.evidence_refs == snapshot.evidence_refs


def test_tampered_evaluation_is_rejected() -> None:
    service, requirements, snapshot, evaluation = _evaluate()
    evaluation.consumer_task_run_id = "task_run_tampered"
    admission = _authorize(service, requirements, snapshot, evaluation)

    assert admission.authorized is False
    assert admission.reason_code == "PHASE_DEPENDENCY_EVALUATION_TAMPERED"


def test_consumed_or_stale_evaluation_cannot_authorize() -> None:
    service, requirements, snapshot, evaluation = _evaluate()
    consumed: set[str] = set()
    first = _authorize(
        service,
        requirements,
        snapshot,
        evaluation,
        consumed_evaluation_ids=consumed,
    )
    replay = _authorize(
        service,
        requirements,
        snapshot,
        evaluation,
        consumed_evaluation_ids=consumed,
    )
    stale = _authorize(
        service,
        requirements,
        snapshot,
        evaluation,
        now=datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert first.authorized is True
    assert replay.authorized is False
    assert replay.reason_code == "PHASE_DEPENDENCY_EVALUATION_REPLAYED"
    assert stale.authorized is False
    assert stale.reason_code == "PHASE_DEPENDENCY_EVALUATION_STALE"
