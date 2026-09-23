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



def _bind_model_option(output: dict, kwargs: dict) -> dict:
    bound = dict(output)
    candidate = dict(bound.get("candidate") or {})
    payload = dict(kwargs.get("payload") or {})
    options = list(payload.get("continuation_options") or [])
    operation_type = str(candidate.get("operation_type") or "")
    requested_actions = set(candidate.get("requested_actions") or [])
    for option in options:
        if str(option.get("operation_type") or "") != operation_type:
            continue
        allowed_actions = set(option.get("allowed_actions") or [])
        if requested_actions.issubset(allowed_actions):
            candidate["option_id"] = option["option_id"]
            break
    bound["candidate"] = candidate
    return bound


class FakeReasoner:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls = 0
        self.last_kwargs = None

    def propose_json(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return {
            "status": "candidate",
            "candidate": _bind_model_option(self.output, kwargs),
            "model_id": "fake-model",
            "response_id": f"fake-response-{self.calls}",
            "real_inference": False,
        }
class SequencedReasoner:
    def __init__(self, outputs: list[dict]) -> None:
        self.outputs = list(outputs)
        self.calls = 0
        self.kwargs_history: list[dict] = []

    def propose_json(self, **kwargs):
        self.kwargs_history.append(kwargs)
        index = min(self.calls, len(self.outputs) - 1)
        self.calls += 1
        return {
            "status": "candidate",
            "candidate": _bind_model_option(self.outputs[index], kwargs),
            "model_id": "fake-model",
            "response_id": f"fake-response-{self.calls}",
            "real_inference": False,
            "evaluation_status": "accepted",
            "warnings": [],
        }


class FakeDemands:
    def __init__(self) -> None:
        self.last_run = None

    def compile_for_run(
        self,
        *,
        run,
        consumer_phase_id: str,
        consumer_operation_type: str | None = None,
        source_step_id: str | None = None,
    ) -> PhaseSemanticDemandCompilation:
        self.last_run = run
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
    materialized = dict(candidate)
    if (
        action == "continue"
        and "option_id" not in materialized
        and materialized.get("runtime_profile")
        and materialized.get("operation_type")
    ):
        materialized["option_id"] = (
            TaskRunPlanner._continuation_option_id(
                runtime_profile=str(
                    materialized["runtime_profile"]
                ),
                operation_type=str(
                    materialized["operation_type"]
                ),
            )
        )
    return {
        "action": action,
        "candidate": materialized,
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
    assert result.candidate.phase_id == "phase_001_patch"
    assert result.candidate.requested_actions == ["apply_patch"]
    assert result.candidate.required_capabilities == ["apply_patch"]
    assert set(result.candidate.runtime_capabilities_required) == {
        "patch_apply",
        "write_workspace",
    }
    assert "policy_decision" not in result.candidate.metadata
    assert result.candidate.metadata["continuation_option_id"] == (
        TaskRunPlanner._continuation_option_id(
            runtime_profile="patch",
            operation_type="patch_apply",
        )
    )



def test_continuation_dependency_demand_uses_consumer_semantic_projection() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
                "phase_id": "planning",
                "operation_type": "patch_preview",
                "contract_type": "patch_request",
                "runtime_profile": "patch",
                "requested_actions": ["patch_preview"],
            }
        )
    )
    demands = FakeDemands()
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=demands,
    )
    run = _run(
        capabilities=["script_execution"],
        semantic_graph={
            "planning_intent": True,
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "planned"
    assert result.candidate is not None
    assert demands.last_run is not None
    consumer_plan = demands.last_run.plan
    canonical = consumer_plan.canonical_execution_plan
    assert canonical is not None
    assert consumer_plan.plan_id != run.plan.plan_id
    assert canonical.operation_kind == "patch_preview"
    assert [step.action for step in canonical.execution_steps] == [
        "patch_preview"
    ]
    assert [step.side_effect for step in canonical.execution_steps] == [False]
    assert set(canonical.required_capabilities) == {
        "patch_apply",
        "write_workspace",
        "patch_preview",
    }
    capability_ids = {
        concept.concept_id
        for concept in consumer_plan.task_semantic_vocabulary.concepts
        if concept.concept_type == "capability"
    }
    assert {
        "patch_apply",
        "write_workspace",
        "patch_preview",
    }.issubset(capability_ids)
    assert result.candidate.requirements.source_plan_id == consumer_plan.plan_id
    assert result.candidate.metadata["source_plan_id"] == consumer_plan.plan_id
    assert result.candidate.metadata["producer_plan_id"] == run.plan.plan_id


def test_continuation_uses_semantic_interpreter_for_bounded_option_selection() -> None:
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
            "requested_effects": ["workspace_mutation"],
        },
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "planned"
    assert reasoner.last_kwargs is not None
    assert reasoner.last_kwargs["role_id"] == "semantic_interpreter"
    payload = reasoner.last_kwargs["payload"]
    assert "runtime_profiles" not in payload
    assert "action_catalog" not in payload
    assert "patch_apply" in payload["allowed_contract_types"]
    assert all(
        isinstance(item, str)
        for item in payload["allowed_contract_types"]
    )
    options = payload["continuation_options"]
    patch_option = next(
        item
        for item in options
        if item["operation_type"] == "patch_apply"
    )
    assert patch_option["option_id"].startswith("opt_")
    assert "runtime_profile" not in patch_option
    assert "apply_patch" in patch_option["allowed_actions"]
    assert "patch_apply" in patch_option["default_contract_types"]
    assert "phase_id" not in payload["output_schema"]["candidate"]
    assert result.candidate is not None
    assert result.candidate.runtime_profile == "patch"
    assert any(
        "option_id" in rule
        for rule in payload["rules"]
    )



def test_continuation_model_prompt_is_bounded_to_pending_effect_catalog() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
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
        capabilities=[
            "apply_patch",
            "modify_file",
            "script_execution",
            "shell_build",
            "shell_test",
            "read_file",
        ],
        semantic_graph={
            "mutation_intent": True,
            "execution_intent": True,
            "requested_effects": [
                "build_execution",
                "runtime_execution",
                "workspace_mutation",
            ],
            "evidence": [f"derived_{index}" for index in range(50)],
        },
    )

    result = planner.plan_continuation(run=run)

    assert result.status == "planned"
    assert reasoner.last_kwargs is not None
    payload = reasoner.last_kwargs["payload"]
    user_prompt = __import__("json").dumps(
        {
            "semantic_goal": reasoner.last_kwargs["semantic_goal"],
            "allowed_fields": reasoner.last_kwargs["allowed_fields"],
            "required_fields": reasoner.last_kwargs["required_fields"],
            "payload": payload,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    assert len(user_prompt) < 6000
    assert len(payload["continuation_options"]) < 20
    assert all(
        option["allowed_actions"]
        for option in payload["continuation_options"]
    )
    assert all(
        option["option_id"].startswith("opt_")
        for option in payload["continuation_options"]
    )
    assert "evidence" not in payload["semantic_intent_graph"]


def test_blocked_terminal_run_does_not_enter_mission_continuation_planner(
    tmp_path: Path,
) -> None:
    class _MustNotPlan:
        def __init__(self) -> None:
            self.calls = 0

        def plan_continuation(self, **_kwargs):
            self.calls += 1
            raise AssertionError("blocked_run_must_not_plan_continuation")

    planner = _MustNotPlan()
    runtime = TaskRuntimeService(
        store=TaskRunStore(root=tmp_path / f"runs_{uuid4().hex}"),
        planner=planner,  # type: ignore[arg-type]
    )
    run = SimpleNamespace(
        status="blocked",
        mission_contract=SimpleNamespace(strategy="end_to_end_governed"),
    )

    assert runtime._continue_terminal_mission(run) is None
    assert planner.calls == 0


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
    assert (
        result.reason_code
        == "MISSION_CONTINUATION_NO_AUTHORIZED_OPTION"
    )


def test_model_phase_id_is_ignored_and_runtime_assigns_fresh_identity() -> None:
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

    assert result.status == "planned"
    assert result.candidate is not None
    assert result.candidate.phase_id == "phase_001_readonly_analysis"
    assert result.candidate.phase_id != "discovery"
    assert reasoner.calls == 1


def test_bounded_candidate_retry_corrects_deterministic_rejection() -> None:
    reasoner = SequencedReasoner(
        [
            _proposal(
                {
                    "phase_id": "model_supplied_ignored",
                    "operation_type": "project_analysis",
                    "contract_type": "patch_apply",
                    "runtime_profile": "patch",
                    "requested_actions": ["apply_patch"],
                }
            ),
            _proposal(
                {
                    "phase_id": "implementation",
                    "operation_type": "patch_apply",
                    "contract_type": "patch_apply",
                    "runtime_profile": "patch",
                    "requested_actions": ["apply_patch"],
                }
            ),
        ]
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
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

    assert result.status == "planned"
    assert result.candidate is not None
    assert result.candidate.phase_id == "phase_001_patch"
    assert reasoner.calls == 2
    correction = reasoner.kwargs_history[1]["payload"][
        "candidate_correction"
    ]
    assert correction["attempt"] == 1
    assert (
        correction["reason_code"]
        == "MISSION_CONTINUATION_OPTION_UNKNOWN"
    )
    assert correction["rejected_option_id"] == (
        TaskRunPlanner._continuation_option_id(
            runtime_profile="patch",
            operation_type="project_analysis",
        )
    )
    assert result.provenance["candidate_retries"] == 1
    assert result.provenance["candidate_rejections"] == [
        "MISSION_CONTINUATION_OPTION_UNKNOWN"
    ]


def test_rejects_premature_complete_with_unsatisfied_effects_after_bounded_retry() -> None:
    reasoner = FakeReasoner(
        _proposal({}, action="complete")
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
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
    assert reasoner.calls == 2
    assert result.provenance["candidate_retries"] == 1
    assert result.provenance["candidate_rejections"] == [
        "MISSION_CONTINUATION_PREMATURE_COMPLETE",
        "MISSION_CONTINUATION_PREMATURE_COMPLETE",
    ]


def test_premature_complete_can_recover_through_bounded_candidate_correction() -> None:
    reasoner = SequencedReasoner(
        [
            _proposal({}, action="complete"),
            _proposal(
                {
                    "phase_id": "implementation",
                    "operation_type": "patch_apply",
                    "contract_type": "patch_apply",
                    "runtime_profile": "patch",
                    "requested_actions": ["apply_patch"],
                }
            ),
        ]
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file", "apply_patch"],
        semantic_graph={
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )
    phase_outcome = SimpleNamespace(
        phase_id="analysis",
        outcome_id="phase_outcome_safe_for_mutation",
        use_safety={"safe_for_destructive_action": True},
        semantic_properties={},
        limitations=[],
        missing_truth=[],
    )

    result = planner.plan_continuation(
        run=run,
        phase_outcome=phase_outcome,
    )

    assert result.status == "planned"
    assert result.candidate is not None
    assert result.candidate.requested_actions == ["apply_patch"]
    assert reasoner.calls == 2
    correction = reasoner.kwargs_history[1]["payload"][
        "candidate_correction"
    ]
    assert correction["reason_code"] == (
        "MISSION_CONTINUATION_PREMATURE_COMPLETE"
    )
    assert correction["rejected_action"] == "complete"
    assert "unsatisfied_requested_effects" not in correction
    assert reasoner.kwargs_history[1]["payload"][
        "unsatisfied_requested_effects"
    ] == ["workspace_mutation"]
    assert len(str(correction)) < 220
    assert result.provenance["candidate_retries"] == 1
    assert result.provenance["candidate_rejections"] == [
        "MISSION_CONTINUATION_PREMATURE_COMPLETE"
    ]


def test_runtime_derives_contract_after_premature_complete_retry() -> None:
    reasoner = SequencedReasoner(
        [
            _proposal({}, action="complete"),
            _proposal(
                {
                    "operation_type": "patch_apply",
                    "contract_type": "patch_request",
                    "runtime_profile": "patch",
                    "requested_actions": ["apply_patch"],
                }
            ),
        ]
    )
    planner = TaskRunPlanner(
        semantic_reasoner=reasoner,
        phase_demands=FakeDemands(),
    )
    run = _run(
        capabilities=["read_file", "apply_patch"],
        semantic_graph={
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )
    phase_outcome = SimpleNamespace(
        phase_id="analysis",
        outcome_id="phase_outcome_safe_for_mutation",
        use_safety={"safe_for_destructive_action": True},
        semantic_properties={},
        limitations=[],
        missing_truth=[],
    )

    result = planner.plan_continuation(
        run=run,
        phase_outcome=phase_outcome,
    )

    assert result.status == "planned"
    assert result.candidate is not None
    assert result.candidate.contract_type == "patch_apply"
    assert result.candidate.runtime_profile == "patch"
    assert result.candidate.requested_actions == ["apply_patch"]
    assert reasoner.calls == 2
    assert result.provenance["candidate_rejections"] == [
        "MISSION_CONTINUATION_PREMATURE_COMPLETE"
    ]
    second_payload = reasoner.kwargs_history[1]["payload"]
    assert "contract_type" not in second_payload["output_schema"]["candidate"]


def test_evidence_repair_without_bounded_target_blocks_before_reasoning() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
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
        capabilities=["read_file", "apply_patch"],
        semantic_graph={
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )
    phase_outcome = SimpleNamespace(
        phase_id="analysis",
        outcome_id="phase_outcome_without_repair_target",
        use_safety={},
        semantic_properties={},
        limitations=["analysis_partial"],
        missing_truth=[],
    )

    result = planner.plan_continuation(
        run=run,
        phase_outcome=phase_outcome,
    )

    assert result.status == "blocked"
    assert result.reason_code == (
        "MISSION_CONTINUATION_EVIDENCE_REPAIR_TARGET_UNAVAILABLE"
    )
    assert reasoner.calls == 0
    assert result.provenance["evidence_repair"]["required"] is True
    assert result.provenance["evidence_repair"]["focus_path_count"] == 0


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
    assert candidate["phase_id"] == "phase_001_readonly_analysis"
    continuation = completed.intent_map["mission_continuation_runtime"]
    assert continuation["status"] == "executed"
    child = store.get_run(continuation["child_task_run_id"])
    assert child is not None
    assert child.status == "completed"
    assert child.current_phase == "phase_001_readonly_analysis"
    assert child.mission_contract is not None
    assert set(child.mission_contract.authority.authorized_capabilities) == {
        "read_file",
        "apply_patch",
    }
    assert child.capabilities_required == ["read_workspace"]
    assert child.intent_map["mission_continuation"]["depth"] == 1
    assert child.intent_map["mission_continuation"]["phase_lineage"] == [
        "discovery",
        "phase_001_readonly_analysis",
    ]
    assert reasoner.calls >= 1


def test_plain_read_files_semantics_are_deterministic() -> None:
    action = TaskRunPlanner().actions.get_action("read_files")
    assert action.semantic_dependency_mode == "deterministic"
    assert action.semantic_use_safety_dimensions == []


def test_continuation_routes_to_readonly_evidence_repair_when_destructive_safety_missing() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
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
        capabilities=[
            "read_file",
            "modify_file",
            "script_execution",
            "shell_build",
            "shell_test",
        ],
        semantic_graph={
            "mutation_intent": True,
            "execution_intent": True,
            "requested_effects": [
                "workspace_mutation",
                "build_execution",
            ],
        },
    )
    focus_paths = [
        f"src/main/Focus{index:02d}.kt"
        for index in range(20)
    ]
    phase_outcome = SimpleNamespace(
        outcome_id="phase_outcome_partial",
        phase_id="discovery",
        use_safety={
            "safe_for_downstream_static_analysis": "true_with_limitations"
        },
        semantic_properties={
            "evidence_repair_focus_paths": focus_paths
        },
        limitations=["file_context_budget_or_omissions"],
        missing_truth=[],
    )

    result = planner.plan_continuation(
        run=run,
        phase_outcome=phase_outcome,
    )

    assert result.status == "planned"
    assert result.candidate is not None
    assert result.candidate.runtime_profile == "readonly_analysis"
    assert result.candidate.requested_actions == ["read_files"]
    repair = result.candidate.metadata["evidence_repair"]
    assert repair["required"] is True
    assert repair["required_use_safety"] == {
        "safe_for_destructive_action": True
    }
    assert repair["focus_path_count"] == 20
    assert repair["focus_paths"] == focus_paths

    assert reasoner.last_kwargs is not None
    payload = reasoner.last_kwargs["payload"]
    assert payload["evidence_repair"]["required"] is True
    assert payload["evidence_repair"]["focus_path_count"] == 20
    assert payload["evidence_repair"]["focus_paths"] == focus_paths[:12]
    assert "evidence_repair_focus_paths" not in payload[
        "terminal_outcome"
    ]["semantic_properties"]
    assert "required_disclosures" not in payload["terminal_outcome"]
    options = payload["continuation_options"]
    assert options
    assert all(
        set(item["allowed_actions"]).issubset(
            {"read_files", "project_analysis"}
        )
        for item in options
    )
    assert not any(
        action in {"write_files", "apply_patch", "run_command", "run_tests"}
        for item in options
        for action in item["allowed_actions"]
    )


def test_continuation_blocks_stalled_evidence_repair_before_reasoning() -> None:
    reasoner = FakeReasoner(
        _proposal(
            {
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
        capabilities=["read_file", "modify_file"],
        semantic_graph={
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )
    run.intent_map["mission_continuation"] = {
        "depth": 4,
        "evidence_repair": {
            "required": True,
            "focus_paths": ["src/A.kt", "src/B.kt"],
        },
    }
    phase_outcome = SimpleNamespace(
        outcome_id="phase_outcome_same_focus",
        phase_id="phase_004_readonly_analysis",
        use_safety={"safe_for_destructive_action": False},
        semantic_properties={
            "evidence_repair_focus_paths": ["src/B.kt", "src/A.kt"]
        },
        limitations=["evidence_repair_focus_unresolved"],
        missing_truth=[],
    )

    result = planner.plan_continuation(
        run=run,
        phase_outcome=phase_outcome,
    )

    assert result.status == "blocked"
    assert result.reason_code == (
        "MISSION_CONTINUATION_EVIDENCE_REPAIR_STALLED"
    )
    assert reasoner.calls == 0
    assert set(result.provenance["previous_focus_paths"]) == {
        "src/A.kt",
        "src/B.kt",
    }
    assert set(
        result.provenance["evidence_repair"]["focus_paths"]
    ) == {"src/A.kt", "src/B.kt"}


def test_continuation_keeps_side_effect_lane_when_destructive_safety_is_proven() -> None:
    planner = TaskRunPlanner()
    run = _run(
        capabilities=["read_file", "modify_file"],
        semantic_graph={
            "mutation_intent": True,
            "requested_effects": ["workspace_mutation"],
        },
    )
    effects = planner._unsatisfied_requested_effects(
        run=run,
        semantic_graph=run.intent_map["semantic_intent_graph"],
        continuation={},
        semantic_context={},
    )
    repair = planner._continuation_evidence_repair_context(
        phase_outcome=SimpleNamespace(
            phase_id="discovery",
            use_safety={"safe_for_destructive_action": True},
            semantic_properties={},
            limitations=[],
            missing_truth=[],
        ),
        unsatisfied_effects=effects,
    )
    options = planner._eligible_continuation_options(
        planner._continuation_option_catalog(run),
        unsatisfied_effects=effects,
        evidence_repair_required=bool(repair),
    )

    assert repair == {}
    assert any(
        "write_files" in option["allowed_actions"]
        or "apply_patch" in option["allowed_actions"]
        for option in options
    )
