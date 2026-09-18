from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionFacet,
    MissionCompletionResolution,
)
from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionCompletionContract,
    MissionContract,
    MissionResourceScope,
)
from aipinho.schemas.runtime.runtime_truth import RuntimeTruth
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_planner import TaskRunPlanner
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


class _CompletionReasoner:
    def __init__(self):
        self.calls = 0

    def propose_json(self, **_kwargs):
        self.calls += 1
        return {
            "status": "candidate",
            "candidate": {
                "action": "complete",
                "candidate": {},
                "confidence": 0.96,
                "rationale": "Frozen semantics indicate no additional phase work.",
            },
            "model_id": "fake-model",
            "response_id": f"fake-complete-{self.calls}",
            "real_inference": False,
        }


class _MissionResolver:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve(
        self,
        *,
        mission_id,
        anchor_run_id=None,
        allow_inference=True,
    ):
        self.calls.append(
            {
                "mission_id": mission_id,
                "anchor_run_id": anchor_run_id,
                "allow_inference": allow_inference,
            }
        )
        return self.resolution


class _TruthPublisher:
    def __init__(self):
        self.calls = []

    def publish(self, run, result, *, runtime_truth=None):
        self.calls.append((run, result, runtime_truth))
        return {"status": "published"}


def _contract(workspace: str) -> MissionContract:
    return MissionContractService().freeze(
        MissionContract(
            mission_id="mission_m9_taskruntime",
            session_id="session_m9_taskruntime",
            source_message_id="message_m9_taskruntime",
            source_prompt_sha256="a" * 64,
            objective="Complete a governed mission.",
            strategy="end_to_end_governed",
            local_resources=[
                MissionResourceScope(
                    resource_id="workspace_target",
                    resource_type="local_workspace",
                    role="target_mutable",
                    locator=workspace,
                    permissions=["read_file"],
                )
            ],
            authority=MissionAuthorityBinding(
                requested_capabilities=["read_file"],
                authorized_capabilities=["read_file"],
            ),
            completion=MissionCompletionContract(
                validation_requirements=["tests_pass"],
                completion_requirements=["validated_change"],
                allow_limited_completion=False,
            ),
            authority_sha256="pending",
        )
    )


def _insufficient_resolution():
    facet = MissionCompletionFacet(
        mission_id="mission_m9_taskruntime",
        snapshot_authority_sha256="b" * 64,
        status="insufficient_evidence",
        safe_to_report_success=False,
        reason_codes=[
            "MISSION_COMPLETION_EVALUATION_MISSING:validation:tests_pass"
        ],
        authority_sha256="c" * 64,
    )
    return MissionCompletionResolution(
        mission_id="mission_m9_taskruntime",
        status="insufficient_evidence",
        reason_codes=list(facet.reason_codes),
        snapshot_authority_sha256="b" * 64,
        catalog_authority_sha256="d" * 64,
        proposal_sha256="e" * 64,
        proposal_source="persisted",
        compilation_status="compiled",
        facet=facet,
    )


def test_terminal_planner_complete_applies_mission_ceiling_before_publish(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = TaskRunStore(root=tmp_path / "runs")
    reasoner = _CompletionReasoner()
    planner = TaskRunPlanner(semantic_reasoner=reasoner)
    resolver = _MissionResolver(_insufficient_resolution())
    publisher = _TruthPublisher()
    runtime = TaskRuntimeService(
        store=store,
        planner=planner,
        mission_completion=resolver,
        result_publisher=publisher,
    )
    contract = _contract(str(workspace))
    run = runtime.create_run(
        TaskRunRequest(
            source_type="direct",
            source_channel="m9_runtime_truth_test",
            session_id=contract.session_id,
            source_message_id=contract.source_message_id,
            mission_contract=contract,
            workspace=str(workspace),
            contract_type="analysis_readonly",
            operation_type="project_analysis",
            runtime_profile="readonly_analysis",
            capabilities_required=["read_workspace"],
            requested_actions=["read_files"],
            intent_map={
                "intent_type": "workspace_fix_request",
                "operation_type": "project_analysis",
                "phase_id": "final_validation",
                "semantic_intent_graph": {
                    "evidence": ["final_phase"],
                    "requested_effects": [],
                },
            },
            policy_decision={
                "status": "allowed",
                "policy_status": "allowed",
                "allowed_actions": ["read_files"],
                "approval_required_for": [],
                "denied_actions": [],
            },
            mode="read_only",
            start_immediately=False,
        )
    )

    completed, result = runtime.start(run.run_id)

    assert completed.status == "completed"
    assert result.status == "completed"
    assert completed.intent_map["mission_continuation_runtime"] == {
        "status": "not_applicable",
        "reason_code": "MISSION_CONTINUATION_PLANNER_COMPLETE",
        "candidate_id": None,
        "child_task_run_id": None,
        "child_status": None,
        "decision_action": None,
        "next_phase": None,
    }
    assert (
        completed.intent_map["mission_completion_runtime"]["status"]
        == "insufficient_evidence"
    )
    assert completed.canonical_state is not None
    assert completed.canonical_state.status == "BLOCKED"
    assert completed.canonical_state.safe_to_report_success is False
    assert [call["allow_inference"] for call in resolver.calls] == [
        True,
        False,
    ]
    assert len(publisher.calls) == 1
    published_truth = publisher.calls[0][2]
    assert published_truth is not None
    assert published_truth.status == "partial"
    assert published_truth.safe_to_report_success is False
    event_types = [event.type for event in runtime.get_events(run.run_id)]
    assert "mission_completion_evaluated" in event_types


def test_intermediate_end_to_end_parent_is_not_published_as_final(
    tmp_path: Path,
) -> None:
    publisher = _TruthPublisher()
    runtime = TaskRuntimeService(
        store=TaskRunStore(root=tmp_path / "runs"),
        result_publisher=publisher,
    )
    run = runtime_run(status="completed")
    run.mission_contract = _contract(str(tmp_path))
    run.mission_binding = run.mission_contract.binding()
    run.intent_map["mission_continuation_runtime"] = {
        "status": "executed",
        "child_task_run_id": "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    }
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="phase completed",
    )
    truth = RuntimeTruth(
        truth_id=f"runtime_truth_{run.run_id}",
        task_run_id=run.run_id,
        status="completed",
        safe_to_report_success=True,
        ui_status="completed",
        speaker_truth_status="allowed",
    )

    runtime._publish_terminal_result(
        run,
        result,
        truth=truth,
    )

    assert publisher.calls == []


def test_blocked_end_to_end_continuation_is_not_published_as_final(
    tmp_path: Path,
) -> None:
    publisher = _TruthPublisher()
    runtime = TaskRuntimeService(
        store=TaskRunStore(root=tmp_path / "runs_blocked"),
        result_publisher=publisher,
    )
    run = runtime_run(status="completed")
    run.mission_contract = _contract(str(tmp_path))
    run.mission_binding = run.mission_contract.binding()
    run.intent_map["mission_continuation_runtime"] = {
        "status": "blocked",
        "reason_code": "MISSION_CONTINUATION_DEPTH_LIMIT_REACHED",
    }
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="phase completed",
    )
    truth = RuntimeTruth(
        truth_id=f"runtime_truth_{run.run_id}",
        task_run_id=run.run_id,
        status="completed",
        safe_to_report_success=True,
        ui_status="completed",
        speaker_truth_status="allowed",
    )

    runtime._publish_terminal_result(
        run,
        result,
        truth=truth,
    )

    assert publisher.calls == []
