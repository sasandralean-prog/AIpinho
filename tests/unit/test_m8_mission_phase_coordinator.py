from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.schemas.runtime.mission_continuation import MissionContinuationCandidate
from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionAuthorityEvidence,
    MissionContract,
    MissionResourceScope,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import DownstreamPhaseRequirements
from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.mission_phase_coordinator_service import MissionPhaseCoordinatorService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def _contract(
    tmp_path: Path,
    *,
    strategy: str = "end_to_end_governed",
    authorized: bool = True,
) -> MissionContract:
    token = uuid4().hex
    resource = MissionResourceScope(
        resource_id=f"workspace_{token[:8]}",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(tmp_path / f"workspace_{token[:8]}"),
        permissions=["read_file"],
        provenance_refs=["m8_b_test"],
    )
    prompt_sha = "d" * 64
    evidence = (
        [
            MissionAuthorityEvidence(
                source_ref=f"msg_{token}",
                clause_sha256="e" * 64,
                source_prompt_sha256=prompt_sha,
                capabilities=["read_workspace"],
            )
        ]
        if authorized
        else []
    )
    contract = MissionContract(
        mission_id=f"mission_{token}",
        session_id=f"session_{token}",
        source_message_id=f"msg_{token}",
        source_prompt_sha256=prompt_sha,
        objective="Continue a generic governed mission.",
        strategy=strategy,
        local_resources=[resource],
        authority=MissionAuthorityBinding(
            requested_capabilities=["read_workspace"],
            authorized_capabilities=["read_workspace"] if authorized else [],
            source_refs=[f"msg_{token}"],
            explicit_evidence=evidence,
        ),
        provenance_refs=[f"source_message:msg_{token}"],
        authority_sha256="pending",
    )
    return MissionContractService().freeze(contract)


def _parent(store: TaskRunStore, contract: MissionContract) -> TaskRun:
    Path(contract.local_resources[0].locator or "").mkdir(parents=True, exist_ok=True)
    run = TaskRun(
        run_id=f"task_run_{uuid4().hex}",
        task_id=f"task_{uuid4().hex}",
        operation_id=f"operation_{uuid4().hex}",
        source_type="test",
        session_id=contract.session_id,
        source_message_id=contract.source_message_id,
        mission_contract=contract,
        mission_binding=contract.binding(),
        workspace=contract.local_resources[0].locator,
        contract_type="analysis_readonly",
        operation_type="project_analysis",
        runtime_profile="readonly_analysis",
        capabilities_required=["read_workspace"],
        requested_actions=["read_workspace"],
        intent_map={"intent_type": "generic_mission", "mission_phase": "phase_1"},
        current_phase="phase_1",
        status="completed",
        plan=TaskRunPlan(
            plan_id=f"plan_{uuid4().hex}",
            contract_type="analysis_readonly",
            status="completed",
            steps=[],
        ),
    )
    store.create_run(run)
    return run


def _outcome(run: TaskRun) -> PhaseOutcome:
    return PhaseOutcome(
        producer_task_run_id=run.run_id,
        producer_operation_id=run.operation_id,
        session_id=run.session_id,
        phase_id="phase_1",
        workspace=run.workspace,
        runtime_status="completed",
        result_status="completed",
        phase_dependency={
            "status": "satisfied",
            "allowed_downstream_uses": ["readonly_followup"],
        },
        use_safety={"safe_for_planning": True},
        semantic_properties={
            "runtime_truth_status": "completed",
            "runtime_truth_safe_to_report_success": True,
        },
        evidence_refs=[f"task_run:{run.run_id}", "artifact:phase_1"],
        result_ref=f"task_run_result:{run.run_id}",
        authority_refs=[f"task_run:{run.run_id}"],
        authority_sha256="f" * 64,
    )


def _candidate(contract: MissionContract) -> MissionContinuationCandidate:
    resource = contract.local_resources[0]
    return MissionContinuationCandidate(
        planner_ref="canonical_execution_plan:generic_phase_2",
        dependency_id="dependency_phase_1_phase_2",
        phase_id="phase_2",
        operation_type="project_analysis",
        contract_type="analysis_readonly",
        runtime_profile="readonly_analysis",
        requested_actions=["read_workspace"],
        required_capabilities=["read_workspace"],
        local_resource_ids=[resource.resource_id],
        workspace_resource_id=resource.resource_id,
        mode="read_only",
        requirements=DownstreamPhaseRequirements(
            contract_id="workflow_generic_readonly_followup",
            consumer_phase_id="phase_2",
            operation_type="project_analysis",
            authority_source="workflow_contract",
            allowed_dependency_statuses=["satisfied"],
            required_downstream_uses=["readonly_followup"],
            required_use_safety={"safe_for_planning": [True]},
            required_capabilities=["read_workspace"],
            evidence_required=True,
        ),
        metadata={
            "policy_decision": {
                "status": "allowed",
                "policy_status": "allowed",
                "allowed_actions": ["read_workspace", "read_files"],
                "approval_required_for": [],
                "denied_actions": [],
            }
        },
    )


def _coordinator(tmp_path: Path, contract: MissionContract):
    store = TaskRunStore(root=tmp_path / f"runs_{uuid4().hex}")
    parent = _parent(store, contract)
    runtime = TaskRuntimeService(store=store)
    coordinator = MissionPhaseCoordinatorService(store=store, runtime=runtime)
    return coordinator, store, parent


def test_materializes_child_through_canonical_taskruntime(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    coordinator, store, parent = _coordinator(tmp_path, contract)
    candidate = _candidate(contract)

    result = coordinator.materialize_next_run(
        previous_run_id=parent.run_id,
        candidate=candidate,
        phase_outcome=_outcome(parent),
        outstanding_completion_requirements=["final_validation"],
    )

    assert result.status == "materialized", result.model_dump(mode="json")
    assert result.reason_code == "mission_continuation_child_materialized"
    assert result.child_task_run_id
    child = store.get_run(result.child_task_run_id)
    assert child is not None
    assert child.parent_task_id == parent.task_id
    assert child.current_phase == "phase_2"
    assert child.bootstrap_context["reservation_status"] == "enriched"
    assert child.mission_contract is not None
    assert child.mission_contract.mission_id == contract.mission_id
    assert child.mission_contract.revision == contract.revision + 1
    assert child.mission_contract.parent_authority_sha256 == contract.authority_sha256
    continuation = child.intent_map["mission_continuation"]
    evaluation = continuation["phase_dependency_evaluation"]
    admission = continuation["phase_dependency_admission"]
    assert evaluation["consumer_task_run_id"] == child.run_id
    assert evaluation["consumer_operation_id"] == child.operation_id
    assert admission["consumer_task_run_id"] == child.run_id
    assert admission["consumer_operation_id"] == child.operation_id
    assert admission["authorized"] is True
    assert child.auto_run_requested is False


def test_materialization_is_idempotent_for_same_candidate(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    coordinator, store, parent = _coordinator(tmp_path, contract)
    candidate = _candidate(contract)
    outcome = _outcome(parent)

    first = coordinator.materialize_next_run(
        previous_run_id=parent.run_id,
        candidate=candidate,
        phase_outcome=outcome,
    )
    second = coordinator.materialize_next_run(
        previous_run_id=parent.run_id,
        candidate=candidate,
        phase_outcome=outcome,
    )

    assert first.status == second.status == "materialized"
    assert first.child_task_run_id == second.child_task_run_id
    assert second.reused_existing_child is True
    children = [
        run
        for run in store.list_runs(session_id=parent.session_id, limit=100)
        if run.parent_task_id == parent.task_id
    ]
    assert len(children) == 1


def test_staged_strategy_does_not_create_child(tmp_path: Path) -> None:
    contract = _contract(tmp_path, strategy="staged")
    coordinator, store, parent = _coordinator(tmp_path, contract)

    result = coordinator.materialize_next_run(
        previous_run_id=parent.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(parent),
    )

    assert result.status == "not_applicable"
    assert result.decision.action == "await_existing_authority"
    children = [
        run
        for run in store.list_runs(session_id=parent.session_id, limit=100)
        if run.parent_task_id == parent.task_id
    ]
    assert children == []


def test_authority_gap_does_not_reserve_child(tmp_path: Path) -> None:
    contract = _contract(tmp_path, authorized=False)
    coordinator, store, parent = _coordinator(tmp_path, contract)

    result = coordinator.materialize_next_run(
        previous_run_id=parent.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(parent),
    )

    assert result.status == "blocked"
    assert result.decision.action == "request_new_authority"
    assert result.decision.authority_gap == ["read_workspace"]
    children = [
        run
        for run in store.list_runs(session_id=parent.session_id, limit=100)
        if run.parent_task_id == parent.task_id
    ]
    assert children == []
