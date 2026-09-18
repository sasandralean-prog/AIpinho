from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.mission_contract import MissionContractBinding
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository
from aipinho.services.runtime.task_run_store import TaskRunStore
from tests.support.runtime_fixtures import runtime_run




class _FakeTimelines:
    def __init__(self, timeline=None) -> None:
        self.timeline = timeline

    def build(self, run_id):
        return self.timeline


class _FakeTruthEngine:
    def __init__(self, truth) -> None:
        self.truth = truth

    def evaluate(self, run, *, result=None, timeline=None):
        return self.truth


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


def _truth(*, status="completed", reason_code="timeline_status:completed", safe=True):
    return SimpleNamespace(
        truth_id="runtime_truth_task_run_phase1",
        status=status,
        reason_code=reason_code,
        safe_to_report_success=safe,
        speaker_truth_status="allowed" if safe else "evidence_required",
        contradictions=[],
        missing_evidence=[],
        model_dump=lambda mode="json": {
            "truth_id": "runtime_truth_task_run_phase1",
            "status": status,
            "reason_code": reason_code,
            "safe_to_report_success": safe,
            "speaker_truth_status": "allowed" if safe else "evidence_required",
            "contradictions": [],
            "missing_evidence": [],
        },
    )


def _fixture():
    phase_dependency = {
        "status": "satisfied_with_limitations",
        "artifact_safe_for_truth_claim": False,
        "artifact_safe_for_catalog": True,
        "artifact_safe_for_planning": "true_with_limitations",
        "artifact_safe_for_downstream_static_analysis": "true_with_limitations",
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


def test_phase_outcome_list_for_mission_rehydrates_chronological_outcomes_after_restart(
    tmp_path,
) -> None:
    root = tmp_path / "runs"
    first_store = TaskRunStore(root=root)
    binding = MissionContractBinding(
        mission_id="mission_restart",
        authority_sha256="a" * 64,
        revision=1,
        source_prompt_sha256="b" * 64,
        strategy="end_to_end_governed",
    )
    first = runtime_run().model_copy(
        update={
            "mission_binding": binding,
            "current_phase": "discovery",
            "created_at": "2026-09-18T09:00:00+00:00",
            "status": "completed",
        }
    )
    second = runtime_run().model_copy(
        update={
            "run_id": "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "task_run_id": "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "mission_binding": binding,
            "current_phase": "validation",
            "created_at": "2026-09-18T09:05:00+00:00",
            "status": "completed",
        }
    )
    unrelated = runtime_run().model_copy(
        update={
            "run_id": "task_run_cccccccccccccccccccccccccccccccc",
            "task_run_id": "task_run_cccccccccccccccccccccccccccccccc",
            "mission_binding": MissionContractBinding(
                mission_id="mission_other",
                authority_sha256="c" * 64,
                revision=1,
                source_prompt_sha256="d" * 64,
                strategy="end_to_end_governed",
            ),
            "current_phase": "other",
            "created_at": "2026-09-18T09:02:00+00:00",
            "status": "completed",
        }
    )
    for run in (first, second, unrelated):
        first_store.create_run(run)
        first_store.save_result(
            run.run_id,
            TaskRunResult(
                run_id=run.run_id,
                status="completed",
                summary=f"{run.current_phase} completed",
            ),
        )

    restarted_store = TaskRunStore(root=root)
    repository = PhaseOutcomeRepository(
        store=restarted_store,
        timelines=_FakeTimelines(),  # type: ignore[arg-type]
        truth=_FakeTruthEngine(_truth()),  # type: ignore[arg-type]
    )

    outcomes = repository.list_for_mission(mission_id="mission_restart")

    assert [item.phase_id for item in outcomes] == ["discovery", "validation"]
    assert [item.producer_task_run_id for item in outcomes] == [
        first.run_id,
        second.run_id,
    ]


def test_phase_outcome_projects_limited_success_without_promoting_truth() -> None:
    run, result = _fixture()
    repository = PhaseOutcomeRepository(
        store=_FakeStore(run, result),  # type: ignore[arg-type]
        timelines=_FakeTimelines(),  # type: ignore[arg-type]
        truth=_FakeTruthEngine(_truth()),  # type: ignore[arg-type]
    )

    outcome = repository.project(run_id=run.run_id)

    assert outcome is not None
    assert outcome.result_status == "completed_with_limitations"
    assert outcome.phase_dependency["status"] == "satisfied_with_limitations"
    assert outcome.use_safety == {
        "safe_for_truth_claim": False,
        "safe_for_catalog": True,
        "safe_for_planning": "true_with_limitations",
        "safe_for_downstream_static_analysis": "true_with_limitations",
        "safe_for_destructive_action": False,
    }
    assert outcome.artifact_refs == ["artifact_inventory"]
    assert "evidence:inventory" in outcome.evidence_refs
    assert outcome.result_ref == "task_run_result:task_run_phase1"
    assert len(outcome.authority_sha256) == 64


def test_phase_outcome_resolve_is_session_and_phase_bound() -> None:
    run, result = _fixture()
    repository = PhaseOutcomeRepository(
        store=_FakeStore(run, result),  # type: ignore[arg-type]
        timelines=_FakeTimelines(),  # type: ignore[arg-type]
        truth=_FakeTruthEngine(_truth()),  # type: ignore[arg-type]
    )

    assert repository.resolve(session_id="session_a", phase_id="phase_1") is not None
    assert repository.resolve(session_id="session_b", phase_id="phase_1") is None
    assert repository.resolve(session_id="session_a", phase_id="phase_2") is None


def test_phase_outcome_blocks_dependency_when_canonical_runtime_truth_blocks() -> None:
    run, result = _fixture()
    blocked_truth = _truth(
        status="blocked",
        reason_code="runtime_truth_contradiction",
        safe=False,
    )
    blocked_truth.contradictions = ["completion_completed_timeline_has_gaps"]
    blocked_truth.model_dump = lambda mode="json": {
        "truth_id": blocked_truth.truth_id,
        "status": blocked_truth.status,
        "reason_code": blocked_truth.reason_code,
        "safe_to_report_success": blocked_truth.safe_to_report_success,
        "speaker_truth_status": blocked_truth.speaker_truth_status,
        "contradictions": blocked_truth.contradictions,
        "missing_evidence": [],
    }
    repository = PhaseOutcomeRepository(
        store=_FakeStore(run, result),  # type: ignore[arg-type]
        timelines=_FakeTimelines(),  # type: ignore[arg-type]
        truth=_FakeTruthEngine(blocked_truth),  # type: ignore[arg-type]
    )

    outcome = repository.project(run_id=run.run_id)

    assert outcome is not None
    assert outcome.phase_dependency["status"] == "blocked"
    assert outcome.phase_dependency["reason_code"] == "runtime_truth_contradiction"
    assert outcome.phase_dependency["runtime_truth_previous_dependency_status"] == "satisfied_with_limitations"
    assert outcome.reason_code == "runtime_truth_contradiction"
    assert outcome.semantic_properties["runtime_truth_status"] == "blocked"
    assert outcome.semantic_properties["runtime_truth_safe_to_report_success"] is False
    assert "completion_completed_timeline_has_gaps" in outcome.missing_truth
    assert "runtime_truth_blocked:runtime_truth_contradiction" in outcome.required_disclosures
    assert f"runtime_truth:{blocked_truth.truth_id}" in outcome.authority_refs
