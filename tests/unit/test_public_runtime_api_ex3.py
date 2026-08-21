from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path

from aipinho.api.routers.public_runtime_api_router import router
from aipinho.schemas.public_runtime_api import PublicRuntimeRequest
from aipinho.services.public_runtime_api_service import ApiVersionManager, PublicContractRegistryService, PublicRuntimeAPI


def test_public_contract_registry_contains_all_public_operations():
    registry = PublicContractRegistryService().list()
    operations = {contract.operation for contract in registry.contracts}

    assert operations == {"chat", "execute", "analyze", "doctor", "validate", "artifacts"}
    assert all(contract.gateway_required for contract in registry.contracts)
    assert all(contract.kernel_required for contract in registry.contracts)
    assert registry.mutates_runtime is False


def test_public_runtime_api_uses_gateway_and_kernel_for_execute():
    response = PublicRuntimeAPI().handle(
        PublicRuntimeRequest(
            operation="execute",
            client_id="cli_public",
            client_type="cli",
            api_version="1.0",
            contract={"contract_type": "execution_plan"},
            payload={"objective": "noop"},
        )
    )

    assert response.status == "accepted"
    assert response.gateway_response.kernel_status == "ready"
    assert response.gateway_required is True
    assert response.kernel_required is True
    assert response.mutates_runtime is False


def test_public_analyze_with_runtime_contract_creates_taskrun_and_artifacts(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "package.json").write_text('{"scripts":{"test":"echo ok"}}\n', encoding="utf-8")
    (workspace / "src").mkdir()
    (workspace / "src" / "main.js").write_text("console.log('ok')\n", encoding="utf-8")

    response = PublicRuntimeAPI().handle(
        PublicRuntimeRequest(
            operation="analyze",
            client_id="rest_public",
            client_type="rest",
            api_version="1.0",
            contract={
                "contract_type": "analysis",
                "operation_type": "workspace_analysis_readonly",
                "runtime_profile": "readonly_analysis",
                "requires_task": True,
                "artifact_generation": True,
                "validation_required": True,
                "workspace_mutation": False,
                "expected_outputs": [
                    "artifact:reports/public_api/analysis.md",
                    "artifact:reports/public_api/inventory.json",
                    "validation_result",
                    "completion_result",
                ],
            },
            payload={
                "objective": "Analyze this project read-only through the public runtime API.",
                "workspace_context": {
                    "project_root": str(workspace),
                    "library_roots": [str(tmp_path / "library")],
                    "readonly_flags": {str(workspace): True},
                },
            },
        )
    )

    assert response.status == "ok"
    assert response.task_run_id and response.task_run_id.startswith("task_run_")
    assert response.task_id and response.task_id.startswith("task_")
    assert len(response.artifact_ids) == 2
    assert response.validation_state["status"] == "passed"
    assert response.completion_state["safe_to_report_success"] is True
    assert response.speaker_truth_state["can_claim_success"] is True
    assert response.gateway_response.status == "accepted"
    assert response.runtime_result["workspace_context"]["library_roots"] == [str(tmp_path / "library")]


def test_public_runtime_contract_that_requires_execution_does_not_silent_accept_without_route():
    response = PublicRuntimeAPI().handle(
        PublicRuntimeRequest(
            operation="execute",
            client_id="rest_public",
            client_type="rest",
            api_version="1.0",
            contract={
                "contract_type": "execution_plan",
                "operation_type": "custom_runtime_operation",
                "runtime_profile": "custom_runtime_profile",
                "requires_task": True,
                "execution_required": True,
                "expected_outputs": ["custom_result"],
            },
            payload={"objective": "Execute a custom runtime operation."},
        )
    )

    assert response.status == "blocked"
    assert response.task_run_id is None
    assert response.artifact_ids == []
    assert response.validation_state["status"] == "blocked"
    assert response.speaker_truth_state["can_claim_success"] is False
    assert response.runtime_result["reason_code"] == "public_runtime_execution_route_missing"


def test_public_execute_shell_contract_creates_taskrun_and_pending_approval_without_shell():
    workspace = Path(r"C:\Dev\AIpinho")

    response = PublicRuntimeAPI().handle(
        PublicRuntimeRequest(
            operation="execute",
            client_id="rest_public",
            client_type="rest",
            api_version="1.0",
            contract={
                "contract_type": "execution_plan",
                "operation_type": "shell_test",
                "runtime_profile": "shell_build_test",
                "requires_task": True,
                "execution_required": True,
                "validation_required": True,
                "workspace_mutation": False,
                "approval_required": True,
                "requested_actions": ["run_command"],
                "expected_outputs": [
                    "command_result",
                    "validation_result",
                    "completion_result",
                    "speaker_truth_result",
                ],
                "command": "gradlew.bat test",
            },
            payload={
                "objective": "Prepare governed test execution without running shell before approval.",
                "workspace_context": {"project_root": str(workspace), "readonly_flags": {str(workspace): True}},
            },
            metadata={"session_id": "public_shell_test_session"},
        )
    )

    assert response.status == "pending_approval"
    assert response.task_run_id and response.task_run_id.startswith("task_run_")
    assert response.task_id and response.task_id.startswith("task_")
    assert response.runtime_result["approval_id"].startswith("approval_")
    assert response.runtime_result["runtime_profile"] == "shell"
    assert response.runtime_result["operation_type"] == "test_run"
    assert response.validation_state["status"] == "waiting_approval"
    assert response.completion_state["status"] == "waiting_approval"
    assert response.speaker_truth_state["can_claim_success"] is False
    assert response.artifact_ids == []
    assert response.runtime_result["reason_code"] == "approval_required_before_shell_execution"


def test_public_runtime_api_blocks_unsupported_version_through_gateway():
    response = PublicRuntimeAPI().handle(
        PublicRuntimeRequest(
            operation="chat",
            client_id="rest_public",
            client_type="rest",
            api_version="0.1",
            contract={"contract_type": "conversation"},
        )
    )

    assert response.status == "blocked"
    assert "gateway_version_not_supported" in response.gateway_response.reason_codes


def test_api_version_manager_reports_supported_versions():
    version = ApiVersionManager().version()

    assert version["api_version"] == "1.0"
    assert "1.0" in version["supported_versions"]


def test_public_runtime_api_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    for path, operation in [
        ("/api/v1/runtime/chat", "chat"),
        ("/api/v1/execute", "execute"),
        ("/api/v1/analyze", "analyze"),
        ("/api/v1/doctor", "doctor"),
        ("/api/v1/validate", "validate"),
        ("/api/v1/artifacts", "artifacts"),
    ]:
        response = client.post(
            path,
            json={
                "client_id": "rest_endpoint",
                "client_type": "rest",
                "api_version": "1.0",
                "operation": operation,
                "contract": {"contract_type": "execution_plan"},
            },
        )
        assert response.status_code == 200
        assert response.json()["gateway_required"] is True
        assert response.json()["kernel_required"] is True
        assert response.json()["gateway_response"]["internal_access_granted"] is False

    assert client.get("/api/v1/runtime").status_code == 200
    assert client.get("/api/v1/modules").status_code == 200
    assert client.get("/api/v1/contracts").status_code == 200
    assert client.get("/api/v1/version").status_code == 200


def test_public_runtime_api_audit_history_records_calls():
    api = PublicRuntimeAPI()
    api.handle(PublicRuntimeRequest(operation="analyze", client_id="web_public", client_type="web", contract={"contract_type": "analysis"}))
    history = api.history()

    assert history["count"] >= 1
    assert history["audits"][-1]["operation"] == "analyze"
    assert history["mutates_runtime"] is False
