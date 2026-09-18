from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionContract,
    MissionResourceScope,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseSemanticDemandCompilation,
)
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_planner import TaskRunPlanner
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class FakeReasoner:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls = 0

    def propose_json(self, **_kwargs):
        self.calls += 1
        return {
            "status": "candidate",
            "candidate": self.output,
            "model_id": "fake-model",
            "response_id": f"fake-response-{self.calls}",
            "real_inference": False,
        }
class FakeDemands:
    def compile_for_run(
        self,
        *,
        run,
        consumer_phase_id: str,
        consumer_operation_type: str | None = None,
        source_step_id: str | None = None,
    ) -> PhaseSemanticDemandCompilation:
        operation = str(consumer_operation_type or "project_analysis")
        requirements = DownstreamPhaseRequirements(
            contract_id=f"fake-demand:{consumer_phase_id}",
            consumer_phase_id=consumer_phase_id,
            operation_type=operation,
            authority_source="workflow_contract",
            allowed_dependency_statuses=["satisfied", "satisfied_with_limitations"],
            required_capabilities=["read_workspace"],
            evidence_required=True,
            source_plan_id=run.plan.plan_id,
            source_execution_id="fake-execution",
            source_semantics_sha256="1" * 64,
        )
        return PhaseSemanticDemandCompilation(
            status="compiled",
            consumer_phase_id=consumer_phase_id,
            consumer_operation_type=operation,
            source_plan_id=run.plan.plan_id,
            source_execution_id="fake-execution",
            source_semantics_sha256="1" * 64,
            requirements=requirements,
        )


def _contract(
    *,
    capabilities: list[str],
    locator: str = r"C:\workspace\target",
    permissions: list[str] | None = None,
) -> MissionContract:
    service = MissionContractService()
    resource = MissionResourceScope(
        resource_id="workspace_target",
        resource_type="local_workspace",
        role="target_mutable",
        locator=locator,
        permissions=list(permissions or capabilities),
    )
    return service.freeze(
        MissionContract(
            mission_id="mission_planner_test",
            session_id="session_planner_test",
            source_message_id="message_planner_test",
            source_prompt_sha256="2" * 64,
            objective="Complete the governed mission using the frozen semantics.",
            strategy="end_to_end_governed",
            local_resources=[resource],
            authority=MissionAuthorityBinding(
                requested_capabilities=capabilities,
                authorized_capabilities=capabilities,
            ),
            authority_sha256="pending",
        )
    )


def _run(
    *,
    capabilities: list[str],
    semantic_graph: dict,
    continuation: dict | None = None,
    requested_actions: list[str] | None = None,
):
    return SimpleNamespace(
        run_id="task_run_planner_parent",
        current_phase="discovery",
        operation_type="project_analysis",
        contract_type="analysis_readonly",
        runtime_profile="readonly_analysis",
        requested_actions=list(requested_actions or ["read_files"]),
        workspace=r"C:\workspace\target",
        mission_contract=_contract(capabilities=capabilities),
        intent_map={
            "intent_type": "generic_mission",
            "operation_type": "project_analysis",
            "phase_id": "discovery",
            "semantic_intent_graph": semantic_graph,
            "future_side_effect_intent": bool(
                semantic_graph.get("mutation_intent")
            ),
            **(
                {"mission_continuation": continuation}
                if continuation is not None
                else {}
            ),
        },
        plan=SimpleNamespace(plan_id="task_run_plan_planner_test"),
    )


def _proposal(candidate: dict, *, action: str = "continue") -> dict:
    return {
        "action": action,
        "candidate": candidate,
        "confidence": 0.93,
        "rationale": "Bounded next work follows from frozen mission semantics.",
    }


def test_plans_candidate_from_catalog_without_candidate_authority() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
                "phase_id": "implementation",
                "operation_type": "patch_apply",
                "contract_type": "patch_apply",
                "runtime_profile": "patch",
                "requested_actions": ["apply_patch"],
            }
        )
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["apply_patch"],
        semantic_graph={
            "mutation_intent": True,
            "execution_intent": False,
            "requested_effects": ["workspace_mutation"],
        },
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "planned"
    assert result.candidate is not None
    assert result.candidate.phase_id == "implementation"
    assert result.candidate.requested_actions == ["apply_patch"]
    assert result.candidate.required_capabilities == ["apply_patch"]
    assert set(result.candidate.runtime_capabilities_required) == {
        "patch_apply",
        "write_workspace",
    }
    assert "policy_decision" not in result.candidate.metadata


def test_rejects_candidate_that_expands_authority() -> None:
    planner = TaskRunPlanner(
        semantic_reasoner=FakeReasoner(
            _proposal(
                {
                    "phase_id": "implementation",
                    "operation_type": "patch_apply",
                    "contract_type": "patch_apply",
                    "runtime_profile": "patch",
                    "requested_actions": ["apply_patch"],
                }
            )
        ),
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file"],
        semantic_graph={"mutation_intent": True, "requested_effects": ["workspace_mutation"]},
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "blocked"
    assert result.reason_code == "MISSION_CONTINUATION_CAPABILITY_NOT_REQUESTED"


def test_rejects_phase_cycle_before_dependency_compilation() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
                "phase_id": "discovery",
                "operation_type": "project_analysis",
                "contract_type": "analysis_readonly",
                "runtime_profile": "readonly_analysis",
                "requested_actions": ["read_files"],
            }
        )
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file"],
        semantic_graph={"planning_intent": True, "requested_effects": []},
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "blocked"
    assert result.reason_code == "MISSION_CONTINUATION_PHASE_CYCLE_DETECTED"


def test_rejects_premature_complete_with_unsatisfied_effects() -> None:
    planner = TaskRunPlanner(
        semantic_reasoner=FakeReasoner(
            _proposal({}, action="complete")
        ),
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file", "apply_patch"],
        semantic_graph={
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "blocked"
    assert result.reason_code == "MISSION_CONTINUATION_PREMATURE_COMPLETE"


def test_depth_limit_blocks_without_calling_reasoner() -> None:
    reasoner = FakeReasoner(_proposal({}, action="complete"))
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file"],
        semantic_graph={"planning_intent": True, "requested_effects": []},
        continuation={"depth": 12},
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "blocked"
    assert result.reason_code == "MISSION_CONTINUATION_DEPTH_LIMIT_REACHED"
    assert reasoner.calls == 0


def test_complete_allowed_after_requested_effect_is_in_history() -> None:
    planner = TaskRunPlanner(
        semantic_reasoner=FakeReasoner(
            _proposal({}, action="complete")
        ),
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file", "apply_patch"],
        semantic_graph={
            "mutation_intent": True,
            "execution_intent": False,
            "requested_effects": ["workspace_mutation"],
        },
        continuation={
            "depth": 1,
            "phase_lineage": ["discovery", "implementation"],
            "history": [
                {
                    "phase_id": "implementation",
                    "requested_actions": ["apply_patch"],
                }
            ],
        },
        requested_actions=["read_files"],
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "not_applicable"
    assert result.reason_code == "MISSION_CONTINUATION_PLANNER_COMPLETE"


def test_taskruntime_terminal_plans_and_executes_child_without_manual_candidate(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    reasoner = FakeReasoner(
        _proposal(
            {
                "phase_id": "followup_analysis",
                "operation_type": "project_analysis",
                "contract_type": "analysis_readonly",
                "runtime_profile": "readonly_analysis",
                "requested_actions": ["read_files"],
            }
        )
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=FakeDemands(),
    )
    store = TaskRunStore(root=tmp_path / f"runs_{uuid4().hex}")
    runtime = TaskRuntimeService(store=store, planner=planner)
    contract = _contract(
        capabilities=["read_file", "apply_patch"],
        locator=str(workspace),
        permissions=["read_file", "apply_patch"],
    )
    run = runtime.create_run(
        TaskRunRequest(
            source_type="direct",
            source_channel="m8_dynamic_planner_test",
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
                "intent_type": "generic_mission",
                "operation_type": "project_analysis",
                "phase_id": "discovery",
                "semantic_intent_graph": {
                    "evidence": ["structured_continuation_test"],
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
    planning = completed.intent_map["mission_continuation_planning"]
    assert planning["status"] == "planned"
    candidate = completed.plan.metadata["mission_continuation_candidate"]
    assert candidate["phase_id"] == "followup_analysis"
    continuation = completed.intent_map["mission_continuation_runtime"]
    assert continuation["status"] == "executed"
    child = store.get_run(continuation["child_task_run_id"])
    assert child is not None
    assert child.status == "completed"
    assert child.current_phase == "followup_analysis"
    assert child.mission_contract is not None
    assert set(child.mission_contract.authority.authorized_capabilities) == {
        "read_file",
        "apply_patch",
    }
    assert child.capabilities_required == ["read_workspace"]
    assert child.intent_map["mission_continuation"]["depth"] == 1
    assert child.intent_map["mission_continuation"]["phase_lineage"] == [
        "discovery",
        "followup_analysis",
    ]
    assert reasoner.calls >= 1
