from __future__ import annotations

import time
from uuid import uuid4

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    PublicRuntimeResponsePolicy,
    ReadonlyAnalysisArtifactRuntimeService,
    ReadonlyArtifactExecution,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


class SlowContinuableRuntime(ReadonlyAnalysisArtifactRuntimeService):
    def execute(self, *, request, workspace: str, label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY") -> ReadonlyArtifactExecution:
        run_id = f"task_run_{uuid4().hex}"
        run = TaskRun(
            run_id=run_id,
            task_id=f"task_{uuid4().hex}",
            operation_id=f"operation_{uuid4().hex}",
            task_run_id=run_id,
            source_type="direct",
            session_id=request.session_id,
            workspace=workspace,
            contract_type="analysis_readonly",
            operation_type="workspace_analysis_readonly",
            runtime_profile="readonly_analysis_artifact_runtime",
            requested_actions=["read_workspace"],
            intent_map={
                "raw_prompt": request.message,
                "intent_type": "workspace_analysis_readonly",
            },
            status="running",
            plan=TaskRunPlan(plan_id=f"plan_{uuid4().hex}", contract_type="analysis_readonly"),
        )
        self.runtime.store.create_run(run)
        time.sleep(0.25)
        return ReadonlyArtifactExecution(
            response=ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=request.session_id,
                status="blocked",
                message="runtime still running",
                operation_type="workspace_analysis_readonly",
                message_type="blocked_policy_message",
                intent={"intent_type": "workspace_analysis_readonly"},
                policy={"safe_to_report_success": False},
                is_final_answer=False,
                grounded=False,
            ),
            run_id=run_id,
            created_artifacts=[],
            validation={"status": "blocked", "safe_to_report_success": False},
        )


def test_public_runtime_returns_accepted_running_for_continuable_long_run(task_runtime_service: TaskRuntimeService) -> None:
    service = SlowContinuableRuntime(
        runtime=task_runtime_service,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=100),
    )
    request = ChatRequest(
        message="Run a readonly analysis and produce reports/example.md",
        session_id="chat_public_boundary_test",
    )

    started = time.monotonic()
    execution = service.start_public_boundary(request=request, workspace=r"C:\Workspace\Generic")
    elapsed_ms = int((time.monotonic() - started) * 1000)

    assert elapsed_ms < 500
    assert execution.response.status == "accepted_running"
    assert execution.run_id
    assert execution.response.task_run_id == execution.run_id
    assert execution.response.result_ref_id == execution.run_id
    assert execution.response.contract_preview["safe_to_report_success"] is False
    assert execution.response.contract_preview["polling"]["summary_url"].endswith(f"/{execution.run_id}/summary")
    events = task_runtime_service.store.get_events(execution.run_id)
    event_types = [event.type for event in events]
    assert "public_response_accepted_running" in event_types
    assert event_types.count("public_response_accepted_running") == 1


def test_accepted_running_summary_is_lightweight_and_not_success(task_runtime_service: TaskRuntimeService) -> None:
    service = SlowContinuableRuntime(
        runtime=task_runtime_service,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=100),
    )
    request = ChatRequest(message="Create reports/example.md from readonly analysis", session_id="chat_summary_test")
    execution = service.start_public_boundary(request=request, workspace=r"C:\Workspace\Generic")

    summary = UniversalTaskSessionService(store=task_runtime_service.store).summary(execution.run_id)

    assert summary is not None
    boundary = summary["public_response_boundary"]
    assert boundary["status"] == "accepted_running"
    assert boundary["polling_available"] is True
    assert boundary["result_finalized"] is False
    assert boundary["safe_to_report_success"] is False
    assert "candidate" not in boundary


def test_public_timeout_blocked_response_is_not_success(task_runtime_service: TaskRuntimeService) -> None:
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=task_runtime_service,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=1),
    )
    response = service._timeout_blocked_response(  # noqa: SLF001 - public boundary contract unit
        ChatRequest(message="Run readonly analysis", session_id="chat_timeout_boundary_test"),
        workspace=r"C:\Workspace\Generic",
        reason_code="PUBLIC_RUNTIME_BLOCKED_BEFORE_ACCEPTED_RUNNING",
        policy=service.public_response_policy,
    )

    assert response.status == "timeout_blocked"
    assert response.policy["public_response_boundary"]["safe_to_report_success"] is False
    assert response.grounding_missing_reason == "PUBLIC_RUNTIME_BLOCKED_BEFORE_ACCEPTED_RUNNING"
