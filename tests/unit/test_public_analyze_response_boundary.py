from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.public_runtime_api import PublicRuntimeRequest
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyArtifactExecution
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.public_runtime_api_service import PublicRuntimeExecutionBridge


class _Store:
    def __init__(self, run: SimpleNamespace) -> None:
        self.run = run

    def get_run(self, run_id: str) -> SimpleNamespace | None:
        return self.run if run_id == self.run.run_id else None


class _ReadonlyRuntime:
    def __init__(self) -> None:
        self.run = SimpleNamespace(
            run_id="task_run_public_boundary",
            task_id="task_public_boundary",
            operation_id="op_public_boundary",
            operation_type="workspace_analysis_readonly",
            runtime_profile="readonly_analysis",
        )
        self.runtime = SimpleNamespace(store=_Store(self.run))
        self.start_public_boundary_called = 0
        self.execute_called = 0

    def start_public_boundary(self, *, request, workspace: str, label: str) -> ReadonlyArtifactExecution:
        self.start_public_boundary_called += 1
        assert workspace
        assert label == "PUBLIC_RUNTIME_ANALYSIS_READY"
        response = ChatResponse(
            response_id="chat_accepted",
            task_id=self.run.task_id,
            task_run_id=self.run.run_id,
            result_ref_id=self.run.run_id,
            operation_id=self.run.operation_id,
            operation_type=self.run.operation_type,
            message_type="task_status_update",
            status="accepted_running",
            message="PUBLIC_RUNTIME_ACCEPTED_RUNNING",
            policy={
                "public_response_boundary": {
                    "status": "accepted_running",
                    "reason_codes": ["RUN_ACCEPTED_ASYNC"],
                    "safe_to_report_success": False,
                }
            },
            contract_preview={
                "polling": {
                    "result_url": f"/api/v1/task-runs/{self.run.run_id}/result",
                    "events_url": f"/api/v1/task-runs/{self.run.run_id}/events",
                }
            },
            governance_lifecycle={
                "speaker_truth": {
                    "can_claim_success": False,
                    "source": "unit_test",
                }
            },
            is_final_answer=False,
            grounded=True,
        )
        return ReadonlyArtifactExecution(
            response=response,
            run_id=self.run.run_id,
            created_artifacts=[],
            validation={
                "status": "accepted_running",
                "reason_code": "RUN_ACCEPTED_ASYNC",
                "safe_to_report_success": False,
            },
        )

    def execute(self, **_: object) -> ReadonlyArtifactExecution:
        self.execute_called += 1
        raise AssertionError("Public analyze should use the timeout-safe boundary.")


def test_public_analyze_returns_polling_handle_from_timeout_safe_boundary() -> None:
    readonly = _ReadonlyRuntime()
    bridge = PublicRuntimeExecutionBridge(readonly_artifact_runtime=readonly)  # type: ignore[arg-type]
    request = PublicRuntimeRequest(
        operation="analyze",
        contract={
            "contract_type": "analysis",
            "operation_type": "workspace_analysis_readonly",
            "runtime_profile": "readonly_analysis",
            "requires_task": True,
            "artifact_generation": True,
            "workspace_mutation": False,
            "expected_outputs": ["artifact:reports/public_api/analysis.md"],
        },
        payload={
            "objective": "Analyze without holding the public HTTP response until runtime completion.",
            "workspace_context": {"project_root": "C:/Dev/AIpinho"},
        },
    )

    result = bridge.execute(request, contract=request.contract, gateway_status="accepted")

    assert readonly.start_public_boundary_called == 1
    assert readonly.execute_called == 0
    assert result["status"] == "accepted_running"
    assert result["reason_code"] == "RUN_ACCEPTED_ASYNC"
    assert result["task_run_id"] == "task_run_public_boundary"
    assert result["operation_id"] == "op_public_boundary"
    assert result["result_endpoint"] == "/api/v1/task-runs/task_run_public_boundary/result"
    assert result["events_endpoint"] == "/api/v1/task-runs/task_run_public_boundary/events"
    assert result["speaker_truth"]["can_claim_success"] is False


def test_public_boundary_matches_workspace_across_windows_separator_forms() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()

    assert service._same_workspace(  # noqa: SLF001 - regression for public boundary run capture
        "C:/Users/rafae/Documents/PinhoabacaxiMusicasDesktop",
        r"C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop",
    )
