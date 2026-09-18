from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionCompletionContract,
    MissionContract,
)
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.mission_completion_projection_service import (
    MissionCompletionProjectionService,
)
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository
from aipinho.services.runtime.task_run_store import TaskRunStore
from tests.support.runtime_fixtures import runtime_run


class _FakeTimelines:
    def build(self, run_id):
        return None


class _FakeTruthEngine:
    def evaluate(self, run, *, result=None, timeline=None):
        return SimpleNamespace(
            truth_id=f"runtime_truth_{run.run_id}",
            status="completed",
            reason_code="result_status:completed",
            safe_to_report_success=True,
            speaker_truth_status="allowed",
            contradictions=[],
            missing_evidence=[],
            model_dump=lambda mode="json": {
                "truth_id": f"runtime_truth_{run.run_id}",
                "status": "completed",
                "reason_code": "result_status:completed",
                "safe_to_report_success": True,
                "speaker_truth_status": "allowed",
                "contradictions": [],
                "missing_evidence": [],
            },
        )


def _parent_contract() -> MissionContract:
    service = MissionContractService()
    return service.freeze(
        MissionContract(
            mission_id="mission_m9_projection",
            session_id="session_m9_projection",
            source_message_id="message_m9_projection",
            source_prompt_sha256="a" * 64,
            objective="Complete a governed multi-phase mission.",
            semantic_context={
                "intent_type": "workspace_fix_request",
                "semantic_intent_graph": {
                    "mutation_intent": True,
                    "execution_intent": True,
                },
            },
            strategy="end_to_end_governed",
            authority=MissionAuthorityBinding(
                requested_capabilities=["read_file", "apply_patch"],
                authorized_capabilities=["read_file", "apply_patch"],
            ),
            completion=MissionCompletionContract(
                validation_requirements=["tests_pass"],
                completion_requirements=["validated_change"],
                allow_limited_completion=True,
            ),
            authority_sha256="pending",
        )
    )


def _repository(store: TaskRunStore) -> PhaseOutcomeRepository:
    return PhaseOutcomeRepository(
        store=store,
        timelines=_FakeTimelines(),  # type: ignore[arg-type]
        truth=_FakeTruthEngine(),  # type: ignore[arg-type]
    )


def _seed_two_revision_mission(root):
    store = TaskRunStore(root=root)
    missions = MissionContractService()
    parent = _parent_contract()
    child = missions.narrowed_child(
        parent,
        additional_validation_requirements=["remote_head_equal"],
        additional_completion_requirements=["promotion_complete"],
        allow_limited_completion=False,
    )
    first = runtime_run().model_copy(
        update={
            "mission_contract": parent,
            "mission_binding": parent.binding(),
            "current_phase": "discovery",
            "created_at": "2026-09-18T09:00:00+00:00",
            "status": "completed",
        }
    )
    second = runtime_run().model_copy(
        update={
            "run_id": "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "task_run_id": "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "mission_contract": child,
            "mission_binding": child.binding(),
            "current_phase": "promotion",
            "created_at": "2026-09-18T09:05:00+00:00",
            "status": "completed",
        }
    )
    for run in (first, second):
        store.create_run(run)
        store.save_result(
            run.run_id,
            TaskRunResult(
                run_id=run.run_id,
                status="completed",
                summary=f"{run.current_phase} completed",
            ),
        )
    return parent, child, first, second


def test_snapshot_merges_strict_completion_contract_and_is_restart_stable(
    tmp_path,
) -> None:
    root = tmp_path / "runs"
    parent, child, first, second = _seed_two_revision_mission(root)
    store = TaskRunStore(root=root)
    service = MissionCompletionProjectionService(
        store=store,
        outcomes=_repository(store),
    )

    snapshot = service.project(mission_id=parent.mission_id)

    assert snapshot.status == "ready"
    assert snapshot.completion_requirements == [
        "validated_change",
        "promotion_complete",
    ]
    assert snapshot.validation_requirements == [
        "tests_pass",
        "remote_head_equal",
    ]
    assert snapshot.allow_limited_completion is False
    assert snapshot.task_run_ids == [first.run_id, second.run_id]
    assert snapshot.phase_outcome_run_ids == [first.run_id, second.run_id]
    assert snapshot.contract_revisions == [1, 2]
    assert snapshot.contract_authority_sha256s == [
        parent.authority_sha256,
        child.authority_sha256,
    ]
    assert len(snapshot.phase_outcome_authority_sha256s) == 2
    assert len(snapshot.authority_sha256) == 64

    restarted_store = TaskRunStore(root=root)
    restarted = MissionCompletionProjectionService(
        store=restarted_store,
        outcomes=_repository(restarted_store),
    ).project(mission_id=parent.mission_id)

    assert restarted.authority_sha256 == snapshot.authority_sha256
    assert restarted.model_dump(exclude={"projected_at"}) == snapshot.model_dump(
        exclude={"projected_at"}
    )


def test_snapshot_fails_closed_on_validly_rehashed_identity_divergence(
    tmp_path,
) -> None:
    root = tmp_path / "runs"
    store = TaskRunStore(root=root)
    missions = MissionContractService()
    parent = _parent_contract()
    divergent = missions.freeze(
        parent.model_copy(
            update={
                "semantic_context": {
                    "intent_type": "different_mission_semantics",
                },
                "revision": 2,
                "parent_authority_sha256": parent.authority_sha256,
                "authority_sha256": "pending",
            }
        )
    )
    first = runtime_run().model_copy(
        update={
            "mission_contract": parent,
            "mission_binding": parent.binding(),
            "current_phase": "discovery",
            "created_at": "2026-09-18T09:00:00+00:00",
            "status": "completed",
        }
    )
    second = runtime_run().model_copy(
        update={
            "run_id": "task_run_cccccccccccccccccccccccccccccccc",
            "task_run_id": "task_run_cccccccccccccccccccccccccccccccc",
            "mission_contract": divergent,
            "mission_binding": divergent.binding(),
            "current_phase": "validation",
            "created_at": "2026-09-18T09:05:00+00:00",
            "status": "completed",
        }
    )
    for run in (first, second):
        store.create_run(run)
        store.save_result(
            run.run_id,
            TaskRunResult(
                run_id=run.run_id,
                status="completed",
                summary="completed",
            ),
        )

    snapshot = MissionCompletionProjectionService(
        store=store,
        outcomes=_repository(store),
    ).project(mission_id=parent.mission_id)

    assert snapshot.status == "invalid"
    assert "MISSION_COMPLETION_CONTRACT_IDENTITY_MISMATCH" in snapshot.reason_codes


def test_snapshot_is_missing_without_mission_runs(tmp_path) -> None:
    store = TaskRunStore(root=tmp_path / "runs")
    snapshot = MissionCompletionProjectionService(
        store=store,
        outcomes=_repository(store),
    ).project(mission_id="mission_absent")

    assert snapshot.status == "missing"
    assert snapshot.reason_codes == ["MISSION_TASK_RUNS_NOT_FOUND"]
