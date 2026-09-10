from __future__ import annotations

import time
from threading import Event

import pytest

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService
from aipinho.services.governance.lifecycle.public_route_lifecycle_service import PublicRouteLifecycleService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    PublicRuntimeResponsePolicy,
    ReadonlyAnalysisArtifactRuntimeService,
)


def _readonly_request(tmp_path, *, operation_id: str = "op_reserved") -> TaskRunRequest:
    return TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id="session_reserved",
        operation_id=operation_id,
        workspace=str(tmp_path),
        contract_type="analysis_readonly",
        operation_type="workspace_analysis_readonly",
        runtime_profile="readonly_analysis",
        capabilities_required=["read_workspace", "artifact_generate"],
        requested_actions=["read_workspace", "artifact_generate"],
        intent_map={
            "intent_type": "workspace_analysis_readonly",
            "requires_task": True,
            "read_only": True,
            "artifact_generation": True,
            "workspace_mutation": False,
        },
        policy_decision={
            "status": "allowed",
            "policy_status": "allowed",
            "allowed_actions": ["read_workspace", "artifact_generate"],
            "approval_required_for": [],
            "denied_actions": [],
        },
        mode="read_only",
    )


def _bind_reservation(request: TaskRunRequest, reservation) -> TaskRunRequest:
    return request.model_copy(
        update={
            "task_id": reservation.task_id,
            "task_run_id": reservation.run_id,
            "operation_id": reservation.operation_id,
            "workspace_id": reservation.workspace_id,
            "project_id": reservation.project_id,
        }
    )


class _BlockingPlanner:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.entered = Event()
        self.release = Event()

    def plan(self, request):
        self.entered.set()
        assert self.release.wait(timeout=5)
        return self.delegate.plan(request)


def test_readonly_artifact_contract_is_executable_without_workspace_mutation() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Analise este workspace em modo somente leitura e gere o artifact "
            "reports/example/analysis.md sem modificar o workspace."
        ),
        source_channel="chat",
        session_id="generic_readonly_artifact",
        workspace_path=r"C:\Workspace\Generic",
    )

    contract = snapshot.operation_contract
    assert contract.operation_type == "workspace_analysis_readonly"
    assert contract.contract_type == "analysis_readonly"
    assert contract.runtime_profile == "readonly_analysis"
    assert contract.read_only is True
    assert contract.requires_task is True
    assert contract.artifact_generation is True
    assert contract.workspace_mutation is False
    assert snapshot.policy.allowed_actions == ["read_workspace", "artifact_generate"]
    assert snapshot.policy.requires_approval is False
    assert snapshot.execution_plan.executable is True
    assert snapshot.execution_plan.executable_plan_ref == f"readonly_analysis:{contract.operation_id}"


def test_readonly_artifact_contract_does_not_override_explicit_deny() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Analise este workspace em modo somente leitura e gere o artifact "
            "reports/example/analysis.md sem modificar o workspace."
        ),
        source_channel="chat",
        workspace_path=r"C:\Workspace\Generic",
        explicit_policy_decisions=["denied"],
    )

    assert snapshot.policy.permission.value == "denied"
    assert snapshot.state.value == "blocked"
    assert snapshot.approval_gate.status == "blocked"


def test_pure_readonly_planning_remains_nonexecuting() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Somente planejamento textual: explique uma estrategia, sem executar e sem criar artefatos.",
        source_channel="chat",
        session_id="generic_readonly_plan",
    )

    assert snapshot.operation_contract.operation_type == "product_planning_readonly"
    assert snapshot.operation_contract.requires_task is False
    assert snapshot.operation_contract.artifact_generation is False
    assert snapshot.operation_contract.workspace_mutation is False
    assert snapshot.execution_plan.executable is False


def test_reservation_is_durable_and_enrichment_updates_the_same_taskrun(task_runtime_service, tmp_path) -> None:
    request = _readonly_request(tmp_path)
    reservation = task_runtime_service.reserve_run(request)

    durable = task_runtime_service.store.get_run(reservation.run_id)
    assert durable is not None
    assert durable.bootstrap_context["reservation_status"] == "durable_pending_enrichment"
    enriched = task_runtime_service.create_run(_bind_reservation(request, reservation))

    assert enriched.run_id == reservation.run_id
    assert enriched.task_id == reservation.task_id
    assert enriched.operation_id == reservation.operation_id
    assert enriched.bootstrap_context["reservation_status"] == "enriched"
    assert len(task_runtime_service.store.list_runs(limit=100)) == 1
    events = task_runtime_service.store.get_events(reservation.run_id)
    assert len([event for event in events if event.type == "run_created"]) == 1
    assert len([event for event in events if event.type == "task_bootstrap_created"]) == 1


def test_public_boundary_returns_durable_identity_before_slow_planning(task_runtime_service, tmp_path) -> None:
    (tmp_path / "README.md").write_text("# fixture\n", encoding="utf-8")
    planner = _BlockingPlanner(task_runtime_service.planner)
    task_runtime_service.planner = planner
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=task_runtime_service,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=20),
    )
    operation_id = "op_public_early_acceptance"

    started = time.monotonic()
    execution = service.start_public_boundary(
        request=ChatRequest(
            message="Analise em somente leitura e gere o artifact reports/example/analysis.md",
            session_id="session_public_early_acceptance",
        ),
        workspace=str(tmp_path),
        operation_id=operation_id,
    )
    elapsed = time.monotonic() - started

    assert planner.entered.is_set()
    assert elapsed < 1.0
    assert execution.response.status == "accepted_running"
    assert execution.run_id is not None
    assert execution.response.task_run_id == execution.run_id
    assert execution.response.operation_id == operation_id
    durable = task_runtime_service.store.get_run(execution.run_id)
    assert durable is not None
    assert durable.operation_id == operation_id
    assert durable.bootstrap_context["reservation_status"] == "durable_pending_enrichment"

    planner.release.set()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        current = task_runtime_service.store.get_run(execution.run_id)
        if current and current.bootstrap_context.get("reservation_status") == "enriched":
            break
        time.sleep(0.02)
    current = task_runtime_service.store.get_run(execution.run_id)
    assert current is not None
    assert current.bootstrap_context.get("reservation_status") == "enriched"
    assert current.operation_id == operation_id
    assert len(task_runtime_service.store.list_runs(limit=100)) == 1


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("operation_id", "op_rebound", "task_run_reservation_operation_mismatch"),
        ("task_id", "task_rebound", "task_run_reservation_task_mismatch"),
    ],
)
def test_reserved_identity_rebinding_fails_closed(task_runtime_service, tmp_path, field, value, reason) -> None:
    request = _readonly_request(tmp_path)
    reservation = task_runtime_service.reserve_run(request)
    bound = _bind_reservation(request, reservation).model_copy(update={field: value})

    with pytest.raises(ValueError, match=f"^{reason}$"):
        task_runtime_service.create_run(bound)

    durable = task_runtime_service.store.get_run(reservation.run_id)
    assert durable is not None
    assert durable.operation_id == reservation.operation_id
    assert durable.task_id == reservation.task_id
    assert durable.bootstrap_context["reservation_status"] == "durable_pending_enrichment"


def test_public_finalization_preserves_existing_operation_id() -> None:
    operation_id = "op_existing_public_operation"
    response = ChatResponse(
        response_id="chat_existing_operation",
        session_id="generic_finalize_identity",
        task_id="task_existing",
        task_run_id="task_run_abcd",
        result_ref_id="task_run_abcd",
        operation_id=operation_id,
        operation_type="workspace_analysis_readonly",
        message_type="task_status_update",
        status="accepted_running",
        message="Accepted",
        intent={
            "intent_type": "workspace_analysis_readonly",
            "requires_task": True,
            "readonly": True,
            "artifact_generation": True,
        },
        policy={"workspace_write": False, "safe_to_report_success": False},
        contract_preview={
            "contract_type": "analysis_readonly",
            "runtime_profile": "readonly_analysis",
            "requires_task": True,
            "artifact_generation": True,
            "workspace_mutation": False,
        },
        is_final_answer=False,
        grounded=True,
    )

    finalized = PublicRouteLifecycleService().finalize_chat_response(
        response,
        prompt="Analise em somente leitura e gere reports/example/analysis.md",
        source_channel="chat",
        workspace_path=r"C:\Workspace\Generic",
    )

    assert finalized.operation_id == operation_id
    assert finalized.governance_lifecycle["operation_contract"]["operation_id"] == operation_id
