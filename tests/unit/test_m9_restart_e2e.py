from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionCompletionContract,
    MissionContract,
    MissionResourceScope,
)
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.runtime.mission_completion_binding_proposal_service import (
    MissionCompletionBindingProposalService,
)
from aipinho.services.runtime.mission_completion_resolution_service import (
    MissionCompletionResolutionService,
)
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_planner import TaskRunPlanner
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class _ContinuationCompleteReasoner:
    def __init__(self):
        self.calls = 0

    def propose_json(self, **_kwargs):
        self.calls += 1
        return {
            "status": "candidate",
            "candidate": {
                "action": "complete",
                "candidate": {},
                "confidence": 0.97,
                "rationale": "No additional bounded phase work remains.",
            },
            "model_id": "fake-continuation-model",
            "response_id": f"continuation-{self.calls}",
            "real_inference": False,
            "warnings": [],
        }


class _CatalogBindingReasoner:
    def __init__(self):
        self.calls = 0

    def propose_json(self, **kwargs):
        self.calls += 1
        payload = kwargs["payload"]
        requirement = dict(payload["requirement"])
        evidence = list(payload["evidence_catalog"])
        assert requirement
        assert evidence
        preferred = next(
            (
                item
                for item in evidence
                if str(item["evidence_ref"]).startswith("task_run:")
            ),
            evidence[0],
        )
        bindings = [
            {
                "requirement": requirement["requirement"],
                "requirement_kind": requirement["requirement_kind"],
                "semantic_relation": "supports",
                "evidence_refs": [preferred["evidence_ref"]],
                "producer_task_run_ids": [
                    preferred["producer_task_run_id"]
                ],
                "confidence": 0.96,
                "rationale": (
                    "Canonical terminal TaskRun evidence semantically "
                    "supports the frozen completion requirement."
                ),
            }
        ]
        return {
            "status": "candidate",
            "candidate": {"bindings": bindings},
            "model_id": "fake-binding-model",
            "response_id": f"binding-{self.calls}",
            "real_inference": False,
            "warnings": [],
        }


class _RejectReasoner:
    def propose_json(self, **_kwargs):
        raise AssertionError(
            "restart RuntimeTruth rehydration must not invoke a model"
        )


class _TruthPublisher:
    def __init__(self):
        self.calls = []

    def publish(self, run, result, *, runtime_truth=None):
        self.calls.append((run.run_id, result.status, runtime_truth))
        return {"status": "published"}


def _contract(workspace: str) -> MissionContract:
    return MissionContractService().freeze(
        MissionContract(
            mission_id="mission_m9_restart_e2e",
            session_id="session_m9_restart_e2e",
            source_message_id="message_m9_restart_e2e",
            source_prompt_sha256="7" * 64,
            objective="Complete the governed mission with evidence.",
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
                completion_requirements=["phase_completed"],
                validation_requirements=[],
                allow_limited_completion=False,
            ),
            authority_sha256="pending",
        )
    )


def _request(contract: MissionContract, workspace: str) -> TaskRunRequest:
    return TaskRunRequest(
        source_type="direct",
        source_channel="m9_restart_e2e",
        session_id=contract.session_id,
        source_message_id=contract.source_message_id,
        mission_contract=contract,
        workspace=workspace,
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
                "evidence": ["terminal_phase"],
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


def test_restart_rehydrates_same_final_runtime_truth_without_model(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    root = tmp_path / "runs"
    store = TaskRunStore(root=root)
    continuation_reasoner = _ContinuationCompleteReasoner()
    binding_reasoner = _CatalogBindingReasoner()
    planner = TaskRunPlanner(
        semantic_reasoner=continuation_reasoner,
    )
    resolution = MissionCompletionResolutionService(
        store=store,
        proposer=MissionCompletionBindingProposalService(
            reasoner=binding_reasoner,  # type: ignore[arg-type]
        ),
    )
    publisher = _TruthPublisher()
    runtime = TaskRuntimeService(
        store=store,
        planner=planner,
        mission_completion=resolution,
        result_publisher=publisher,
    )
    contract = _contract(str(workspace))
    run = runtime.create_run(_request(contract, str(workspace)))

    completed, result = runtime.start(run.run_id)

    assert completed.status == "completed"
    assert result.status == "completed"
    assert completed.canonical_state is not None
    assert completed.canonical_state.status == "COMPLETED"
    assert completed.canonical_state.safe_to_report_success is True
    assert binding_reasoner.calls == 1
    assert len(publisher.calls) == 1
    assert publisher.calls[0][2] is not None
    assert publisher.calls[0][2].safe_to_report_success is True

    persisted = store.get_run(run.run_id)
    assert persisted is not None
    assert (
        "mission_completion_binding_proposal"
        in persisted.intent_map
    )
    assert (
        persisted.intent_map["mission_completion_runtime"]["status"]
        == "ready"
    )

    before = runtime.get_runtime_truth(run.run_id)
    assert before is not None
    assert before.status == "completed"
    assert before.safe_to_report_success is True
    assert before.mission_completion_status == "ready"
    assert binding_reasoner.calls == 1
    before_events = [
        event.type for event in runtime.get_events(run.run_id)
    ]
    assert before_events.count("mission_completion_evaluated") == 1

    restarted_store = TaskRunStore(root=root)
    restarted_resolution = MissionCompletionResolutionService(
        store=restarted_store,
        proposer=MissionCompletionBindingProposalService(
            reasoner=_RejectReasoner(),  # type: ignore[arg-type]
        ),
    )
    restarted_runtime = TaskRuntimeService(
        store=restarted_store,
        mission_completion=restarted_resolution,
        result_publisher=_TruthPublisher(),
    )

    after = restarted_runtime.get_runtime_truth(run.run_id)

    assert after is not None
    assert after.model_dump(mode="json") == before.model_dump(mode="json")
    assert after.mission_completion_status == "ready"
    assert after.mission_completion_authority_sha256 == (
        before.mission_completion_authority_sha256
    )
    after_events = [
        event.type for event in restarted_runtime.get_events(run.run_id)
    ]
    assert after_events.count("mission_completion_evaluated") == 1
