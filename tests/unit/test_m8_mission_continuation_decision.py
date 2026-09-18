from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.schemas.runtime.mission_continuation import MissionContinuationCandidate
from aipinho.schemas.runtime.mission_contract import (
    MissionAuthorityBinding,
    MissionAuthorityEvidence,
    MissionCompletionContract,
    MissionContract,
    MissionResourceScope,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import DownstreamPhaseRequirements
from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.runtime.mission_continuation_service import MissionContinuationService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_store import TaskRunStore


def _contract(
    tmp_path: Path,
    *,
    strategy: str = "end_to_end_governed",
    requested: list[str] | None = None,
    authorized: list[str] | None = None,
) -> MissionContract:
    requested = requested or ["read_workspace", "modify_file"]
    authorized = authorized if authorized is not None else list(requested)
    token = uuid4().hex
    target = MissionResourceScope(
        resource_id=f"target_{token[:8]}",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(tmp_path / "target"),
        permissions=["read_file", "modify_file"],
        provenance_refs=["m8_test"],
    )
    source = MissionResourceScope(
        resource_id=f"source_{token[:8]}",
        resource_type="local_workspace",
        role="source_readonly",
        locator=str(tmp_path / "source"),
        permissions=["read_file"],
        provenance_refs=["m8_test"],
    )
    prompt_sha = "a" * 64
    evidence = [
        MissionAuthorityEvidence(
            source_ref=f"msg_{token}",
            clause_sha256=("b" * 63) + str(index % 10),
            source_prompt_sha256=prompt_sha,
            capabilities=[capability],
        )
        for index, capability in enumerate(authorized)
    ]
    contract = MissionContract(
        mission_id=f"mission_{token}",
        session_id=f"session_{token}",
        source_message_id=f"msg_{token}",
        source_prompt_sha256=prompt_sha,
        objective="Continue a governed multi-phase mission.",
        strategy=strategy,
        local_resources=[target, source],
        authority=MissionAuthorityBinding(
            requested_capabilities=requested,
            authorized_capabilities=authorized,
            source_refs=[f"msg_{token}"],
            explicit_evidence=evidence,
        ),
        completion=MissionCompletionContract(
            validation_requirements=["final_validation"],
            completion_requirements=["promotion_complete"],
        ),
        provenance_refs=[f"source_message:msg_{token}"],
        authority_sha256="pending",
    )
    return MissionContractService().freeze(contract)


def _run(store: TaskRunStore, contract: MissionContract, *, status: str = "completed") -> TaskRun:
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
        intent_map={"mission_phase": "discovery"},
        current_phase="discovery",
        status=status,
        plan=TaskRunPlan(
            plan_id=f"plan_{uuid4().hex}",
            contract_type="analysis_readonly",
            status="completed" if status in {"completed", "partial"} else "pending",
            steps=[],
        ),
    )
    store.create_run(run)
    return run


def _outcome(run: TaskRun, *, dependency_status: str = "satisfied", safe_for_planning=True) -> PhaseOutcome:
    return PhaseOutcome(
        producer_task_run_id=run.run_id,
        producer_operation_id=run.operation_id,
        session_id=run.session_id,
        phase_id="discovery",
        workspace=run.workspace,
        runtime_status=str(run.status),
        result_status="completed" if dependency_status == "satisfied" else "completed_with_limitations",
        phase_dependency={
            "status": dependency_status,
            "allowed_downstream_uses": ["patch_planning"],
            "forbidden_downstream_uses": [],
            "forbidden_downstream_claims": [],
        },
        use_safety={"safe_for_planning": safe_for_planning},
        semantic_properties={
            "runtime_truth_status": "completed",
            "runtime_truth_safe_to_report_success": True,
        },
        evidence_refs=[f"task_run:{run.run_id}", f"artifact:{run.run_id}"],
        result_ref=f"task_run_result:{run.run_id}",
        authority_refs=[f"task_run:{run.run_id}"],
        authority_sha256="c" * 64,
    )


def _candidate(contract: MissionContract, **updates) -> MissionContinuationCandidate:
    target = contract.local_resources[0]
    values = {
        "planner_ref": "canonical_execution_plan:plan_patch",
        "dependency_id": "dependency_discovery_patch",
        "phase_id": "patch_planning",
        "operation_type": "patch_planning",
        "contract_type": "analysis_readonly",
        "runtime_profile": "readonly_analysis",
        "requested_actions": ["read_workspace"],
        "required_capabilities": ["modify_file"],
        "local_resource_ids": [target.resource_id],
        "remote_resource_ids": [],
        "requirements": DownstreamPhaseRequirements(
            contract_id="workflow_patch_planning",
            consumer_phase_id="patch_planning",
            operation_type="patch_planning",
            authority_source="workflow_contract",
            allowed_dependency_statuses=["satisfied", "satisfied_with_limitations"],
            required_downstream_uses=["patch_planning"],
            required_use_safety={"safe_for_planning": [True, "true_with_limitations"]},
            required_capabilities=["modify_file"],
            evidence_required=True,
        ),
    }
    values.update(updates)
    return MissionContinuationCandidate(**values)


def _service(tmp_path: Path, contract: MissionContract, *, status: str = "completed"):
    store = TaskRunStore(root=tmp_path / f"task_runs_{uuid4().hex}")
    run = _run(store, contract, status=status)
    return MissionContinuationService(store=store), run


def test_end_to_end_candidate_continues_with_monotonic_child_contract(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    service, run = _service(tmp_path, contract)
    candidate = _candidate(contract)
    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=candidate,
        phase_outcome=_outcome(run),
        outstanding_completion_requirements=["promotion_complete"],
    )

    assert decision.action == "continue_to_next_phase"
    assert decision.reason_code == "mission_continuation_existing_authority_and_evidence_allow"
    assert decision.child_contract is not None
    child = decision.child_contract
    assert child.revision == contract.revision + 1
    assert child.parent_authority_sha256 == contract.authority_sha256
    assert child.authority.requested_capabilities == ["modify_file"]
    assert child.authority.authorized_capabilities == ["modify_file"]
    assert [item.resource_id for item in child.local_resources] == [contract.local_resources[0].resource_id]
    assert MissionContractService().verify(child)
    assert decision.dependency_evaluation is not None
    assert decision.dependency_evaluation.decision == "ADMITTED"


def test_runtime_truth_or_dependency_block_stops_continuation(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    service, run = _service(tmp_path, contract)
    outcome = _outcome(run, dependency_status="blocked")
    outcome = outcome.model_copy(
        update={
            "semantic_properties": {
                **outcome.semantic_properties,
                "runtime_truth_status": "blocked",
                "runtime_truth_safe_to_report_success": False,
            }
        }
    )

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=outcome,
    )

    assert decision.action == "block"
    assert decision.reason_code == "mission_continuation_upstream_truth_blocked"
    assert decision.child_contract is None


def test_missing_candidate_capability_requests_new_authority(tmp_path: Path) -> None:
    contract = _contract(
        tmp_path,
        requested=["read_workspace", "modify_file"],
        authorized=["read_workspace"],
    )
    service, run = _service(tmp_path, contract)

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(run),
    )
    assert decision.action == "request_new_authority"
    assert decision.reason_code == "mission_continuation_authority_gap"
    assert decision.authority_gap == ["modify_file"]
    assert decision.child_contract is None


def test_staged_strategy_stops_at_boundary_even_when_authority_exists(tmp_path: Path) -> None:
    contract = _contract(tmp_path, strategy="staged")
    service, run = _service(tmp_path, contract)

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(run),
    )

    assert decision.action == "await_existing_authority"
    assert decision.reason_code == "mission_continuation_staged_boundary"
    assert decision.child_contract is not None


def test_single_operation_does_not_invent_multiphase_continuation(tmp_path: Path) -> None:
    contract = _contract(tmp_path, strategy="single_operation")
    service, run = _service(tmp_path, contract)

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(run),
        outstanding_completion_requirements=["promotion_complete"],
    )

    assert decision.action == "block"
    assert decision.reason_code == "mission_continuation_single_operation_has_outstanding_requirements"
    assert decision.child_contract is None


def test_single_operation_completes_when_no_requirements_remain(tmp_path: Path) -> None:
    contract = _contract(tmp_path, strategy="single_operation")
    service, run = _service(tmp_path, contract)

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(run),
    )

    assert decision.action == "complete"
    assert decision.reason_code == "mission_continuation_single_operation_complete"
    assert decision.child_contract is None


def test_nonterminal_previous_run_fails_closed(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    service, run = _service(tmp_path, contract, status="running")

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(run),
    )

    assert decision.action == "block"
    assert decision.reason_code == "mission_continuation_previous_run_not_terminal"


def test_candidate_cannot_expand_resource_scope(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    service, run = _service(tmp_path, contract)
    candidate = _candidate(contract, local_resource_ids=["resource_not_in_mission"])

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=candidate,
        phase_outcome=_outcome(run),
    )

    assert decision.action == "block"
    assert decision.reason_code == "mission_continuation_local_resource_out_of_scope"


def test_dependency_requirements_can_block_even_with_human_authority(tmp_path: Path) -> None:
    contract = _contract(tmp_path)
    service, run = _service(tmp_path, contract)

    decision = service.decide(
        previous_run_id=run.run_id,
        candidate=_candidate(contract),
        phase_outcome=_outcome(run, safe_for_planning=False),
    )

    assert decision.action == "block"
    assert decision.dependency_evaluation is not None
    assert decision.dependency_evaluation.decision == "BLOCKED"
    assert decision.child_contract is None
