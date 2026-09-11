from __future__ import annotations

from types import SimpleNamespace

from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository


class _FakeStore:
    def __init__(self, run, result) -> None:
        self.run = run
        self.result = result

    def list_runs(self, *, session_id=None, limit=1000):
        if session_id and self.run.session_id != session_id:
            return []
        return [self.run]

    def get_run(self, run_id):
        return self.run if run_id == self.run.run_id else None

    def get_result(self, run_id):
        return self.result if run_id == self.run.run_id else None


def _fixture():
    phase_dependency = {
        "status": "satisfied_with_limitations",
        "artifact_safe_for_truth_claim": False,
        "artifact_safe_for_catalog": True,
        "artifact_safe_for_planning": "true_with_limitations",
        "artifact_safe_for_destructive_action": False,
        "allowed_downstream_uses": ["catalog_planning_with_limitations"],
        "forbidden_downstream_claims": ["full_truth"],
    }
    semantic = {
        "status": "completed_with_limitations",
        "reason_code": "CATALOG_READY_WITH_INFERRED_AND_UNKNOWN_IDENTITY",
        "phase_contract_status": "satisfied_with_limitations",
        "artifact_sufficiency_status": "catalog_planning_accepted_with_truth_limitations",
        "safe_for_limited_discovery": True,
        "partial_artifact_accepted": True,
        "phase_dependency": phase_dependency,
    }
    run = SimpleNamespace(
        run_id="task_run_phase1",
        operation_id="operation_phase1",
        session_id="session_a",
        workspace="D:/corpus",
        status="completed_with_limitations",
        current_phase="phase_1",
        intent_map={},
        bootstrap_context={},
        canonical_state=None,
        produced_artifacts=[
            {
                "artifact_id": "artifact_inventory",
                "status": "partial",
                "evidence_refs": ["evidence:inventory"],
            }
        ],
    )
    result = SimpleNamespace(
        status="completed_with_limitations",
        reason_code="CATALOG_READY_WITH_INFERRED_AND_UNKNOWN_IDENTITY",
        outputs={"phase_semantic_completion_decision": semantic},
        completion=SimpleNamespace(
            metadata={
                "phase_dependency": phase_dependency,
                "required_disclosures": ["identity_not_observed"],
            }
        ),
        limitations=["identity_not_observed"],
    )
    return run, result


def test_phase_outcome_projects_limited_success_without_promoting_truth() -> None:
    run, result = _fixture()
    repository = PhaseOutcomeRepository(store=_FakeStore(run, result))  # type: ignore[arg-type]

    outcome = repository.project(run_id=run.run_id)

    assert outcome is not None
    assert outcome.result_status == "completed_with_limitations"
    assert outcome.phase_dependency["status"] == "satisfied_with_limitations"
    assert outcome.use_safety == {
        "safe_for_truth_claim": False,
        "safe_for_catalog": True,
        "safe_for_planning": "true_with_limitations",
        "safe_for_destructive_action": False,
    }
    assert outcome.artifact_refs == ["artifact_inventory"]
    assert "evidence:inventory" in outcome.evidence_refs
    assert outcome.result_ref == "task_run_result:task_run_phase1"
    assert len(outcome.authority_sha256) == 64


def test_phase_outcome_resolve_is_session_and_phase_bound() -> None:
    run, result = _fixture()
    repository = PhaseOutcomeRepository(store=_FakeStore(run, result))  # type: ignore[arg-type]

    assert repository.resolve(session_id="session_a", phase_id="phase_1") is not None
    assert repository.resolve(session_id="session_b", phase_id="phase_1") is None
    assert repository.resolve(session_id="session_a", phase_id="phase_2") is None
