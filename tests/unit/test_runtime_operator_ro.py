from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.runtime_operator_router import router
from aipinho.core.paths import PATHS
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.runtime.runtime_operator import ExpectedRuntimeContract
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.runtime.runtime_operator_doctor_service import RuntimeExplainerService, RuntimeOperatorDoctorService, RuntimePatchPlannerService
from aipinho.services.runtime.runtime_operator_doctor_service import FireTestDoctorService
from aipinho.services.runtime.runtime_operator_service import RuntimeOperatorService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def _runtime_data():
    return {
        "task_id": "task_1",
        "task_run_id": "run_1",
        "operation_id": "op_1",
        "intent_type": "conversation",
        "status": "COMPLETED",
        "workspace_context": {"project_root": r"C:\Dev\AIpinho"},
        "validation": "passed",
        "completion": "completed",
        "speaker_truth": "success",
        "artifacts": ["artifact_1"],
        "isr": {"intent": "conversation"},
        "plan": {"stages": ["answer"]},
        "approval": "not_required",
        "dispatch": "ready",
        "role_selection": ["analyst"],
        "runtime_contracts": {"version": "2.0"},
        "events": [{"sequence": 1, "event_type": "task_created"}],
        "executor": "not_started",
        "models": {"SemanticUnderstanding": "qwen"},
        "tools": [],
        "skills": [],
    }


def test_runtime_operator_snapshot_is_read_only_and_has_no_side_effects():
    snapshot = RuntimeOperatorService().snapshot(runtime_data=_runtime_data())

    assert snapshot.task_run_id == "run_1"
    assert snapshot.current_intent.value == "conversation"
    assert snapshot.current_workspace.value == {"project_root": r"C:\Dev\AIpinho"}
    assert snapshot.read_only is True
    assert snapshot.side_effects is False


def test_runtime_operator_snapshot_normalizes_public_chat_response_envelope():
    snapshot = RuntimeOperatorService().snapshot(
        runtime_data={
            "chat_response": {
                "task_id": "task_public",
                "result_ref_id": "task_run_public",
                "operation_id": "op_public",
                "session_id": "session_public",
                "intent": {"intent_type": "workspace_analysis_readonly", "requires_task": True},
                "policy": {"approval_required_for": []},
                "artifact_links": [{"artifact_id": "artifact_public", "logical_path": "reports/discovery.md"}],
                "governance_lifecycle": {
                    "workspace_path": r"C:\Project Root",
                    "operation_contract": {
                        "contract_type": "analysis_readonly",
                        "runtime_profile": "readonly_analysis",
                    },
                    "execution_plan": {"executable": True},
                    "validation": {"status": "passed"},
                    "completion": {"status": "completed"},
                    "speaker_truth": {"status": "completed", "safe_to_report_success": True},
                },
            }
        }
    )

    assert snapshot.task_id == "task_public"
    assert snapshot.task_run_id == "task_run_public"
    assert snapshot.current_intent.value["intent_type"] == "workspace_analysis_readonly"
    assert snapshot.current_workspace.value == {"project_root": r"C:\Project Root"}
    assert snapshot.current_contracts.value["contract_type"] == "analysis_readonly"
    assert snapshot.current_validation.value["status"] == "passed"
    assert snapshot.current_completion.value["status"] == "completed"
    assert snapshot.current_speaker_truth.value["safe_to_report_success"] is True
    assert snapshot.current_artifacts.value[0]["artifact_id"] == "artifact_public"
    assert snapshot.current_artifacts.value[0]["logical_path"] == "reports/discovery.md"


def test_firetest_doctor_normalizes_top_level_public_chat_response():
    raw = {
        "task_id": "task_public",
        "result_ref_id": "task_run_public",
        "operation_id": "op_public",
        "session_id": "session_public",
        "intent": {"intent_type": "workspace_analysis_readonly", "requires_task": True},
        "artifact_links": [
            {"artifact_id": "artifact_1", "label": "reports/phase3.md"},
            {"artifact_id": "artifact_2", "label": "reports/comparison.md"},
        ],
        "governance_lifecycle": {
            "state": "completed",
            "operation_contract": {
                "contract_type": "analysis_readonly",
                "runtime_profile": "readonly_analysis",
            },
            "execution_plan": {"executable": True},
            "validation": {"status": "passed"},
            "completion": {"status": "completed"},
            "speaker_truth": {"can_claim_success": True},
        },
    }

    result = FireTestDoctorService().analyze(
        raw,
        ExpectedRuntimeContract(
            intent={"intent_type": "workspace_analysis_readonly"},
            lifecycle={"status": "completed"},
            artifacts={"count": 2, "required": ["reports/phase3.md", "reports/comparison.md"]},
            validation={"status": "passed"},
            completion={"status": "completed"},
            speaker_truth={"safe_to_report_success": True},
            execution_plan={"executable": True},
            contracts={"contract_type": "analysis_readonly", "runtime_profile": "readonly_analysis"},
        ),
    )

    assert result.doctor_report.status == "passed"
    assert result.regression_matrix.status_for("Artifacts") == "PASS"
    assert result.patch_plan.status == "no_patch_needed"


def test_firetest_doctor_treats_safe_missing_executable_plan_block_as_expected():
    raw = {
        "operation_id": "op_public",
        "session_id": "session_public",
        "status": "preview",
        "intent": {"intent_type": "patch_or_write_request", "requires_task": True},
        "policy": {"permission": "ask", "approval_required_for": ["apply_patch"], "approval_created": False},
        "governance_lifecycle": {
            "state": "plan_only_preview",
            "execution_plan": {
                "preview_kind": "plan_only_preview",
                "executable": False,
                "executable_plan_ref": None,
                "blocked_reason": "APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN",
            },
            "approval_gate": {
                "required": True,
                "can_create_approval": False,
                "approval_id": None,
                "status": "APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN",
            },
            "validation": {"status": "not_run"},
            "completion": {"status": "incomplete", "safe_to_report_success": False},
            "speaker_truth": {"can_claim_success": False, "safe_to_report_success": False},
        },
    }

    result = FireTestDoctorService().analyze(
        raw,
        ExpectedRuntimeContract(
            intent={"requires_task": True},
            approval={"required": True, "approval_created": False},
            execution_plan={
                "required": True,
                "executable": False,
                "blocked_reason": "APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN",
            },
            validation={"status": "not_run"},
            completion={"safe_to_report_success": False},
            speaker_truth={"safe_to_report_success": False},
        ),
    )

    assert result.doctor_report.status == "passed"
    assert result.regression_matrix.status_for("Approval") == "PASS"
    assert result.regression_matrix.status_for("ExecutionPlan") == "PASS"
    assert result.patch_plan.status == "no_patch_needed"


def test_runtime_operator_snapshot_hydrates_real_task_run(tmp_path):
    root = PATHS.project_root / "data" / "tmp_runtime_operator_tests" / uuid4().hex
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "package.json").write_text('{"scripts":{"test":"echo ok"}}\n', encoding="utf-8")
    store = TaskRunStore(root / "task_runs")
    artifacts = UniversalArtifactRegistryService(
        registry=ArtifactRegistryRepository(root / "artifact_registry.json"),
        store_root=root / "artifacts",
    )
    runtime = TaskRuntimeService(store=store)
    readonly = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        artifacts=artifacts,
        phase_store_path=root / "phase_store.json",
    )
    response = CanonicalPublicChatService(readonly_artifact_runtime=readonly).respond(
        ChatRequest(
            session_id="snapshot_hydration",
            message=f'Fase 1. Analise "{workspace}" read-only e gere artifacts reports/snapshot.md.',
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    snapshot = RuntimeOperatorService(store=store).snapshot(task_run_id=str(response.result_ref_id))

    assert snapshot.task_run_id == response.result_ref_id
    assert snapshot.task_id == response.task_id
    assert snapshot.task_id
    assert snapshot.operation_id
    assert snapshot.current_intent.value == "workspace_analysis_readonly"
    assert snapshot.current_lifecycle.value == "completed"
    assert snapshot.current_workspace.status == "observed"
    assert snapshot.current_artifacts.value
    assert snapshot.current_validation.value["status"] == "passed"
    assert snapshot.current_completion.value["status"] == "completed"
    assert snapshot.current_speaker_truth.value["safe_to_report_success"] is True
    assert snapshot.timeline.value["observable"] is True


def test_runtime_doctor_builds_deterministic_regression_matrix():
    snapshot = RuntimeOperatorService().snapshot(runtime_data=_runtime_data())
    expected = ExpectedRuntimeContract(
        intent="workspace_analysis_readonly",
        lifecycle="COMPLETED",
        workspace={"project_root": r"C:\Dev\AIpinho"},
        validation="passed",
        completion="completed",
        speaker_truth="success",
        roles=["analyst"],
    )

    report = RuntimeOperatorDoctorService().analyze(snapshot, expected)

    assert report.status == "regressions_found"
    assert report.deterministic is True
    assert report.read_only is True
    assert report.side_effects is False
    assert report.matrix.status_for("Intent") == "FAIL"
    assert report.matrix.status_for("Lifecycle") == "PASS"
    assert report.findings[0].reason_code == "intent_regression"
    assert report.summary.status == "FAIL"
    assert report.evidence
    assert report.recommendations
    assert report.metadata.generated_artifacts == ["runtime_doctor_report.json", "runtime_doctor.md"]
    assert "Runtime Doctor Report" in (report.markdown or "")
    assert "category,status,severity,reason_code" in (report.csv or "")


def test_runtime_doctor_passes_when_expected_contract_matches():
    snapshot = RuntimeOperatorService().snapshot(runtime_data=_runtime_data())
    expected = ExpectedRuntimeContract(
        intent="conversation",
        lifecycle="COMPLETED",
        workspace={"project_root": r"C:\Dev\AIpinho"},
        validation="passed",
        completion="completed",
        speaker_truth="success",
        roles=["analyst"],
    )

    report = RuntimeOperatorDoctorService().analyze(snapshot, expected)

    assert report.status == "passed"
    assert report.findings == []
    assert report.matrix.status_for("Intent") == "PASS"


def test_runtime_doctor_treats_expected_dict_as_minimum_contract():
    snapshot = RuntimeOperatorService().snapshot(
        runtime_data={
            **_runtime_data(),
            "completion": {
                "status": "waiting_input",
                "source": "run_status_without_result",
                "safe_to_report_success": False,
                "missing_outputs": [],
            },
            "speaker_truth": {
                "runtime_status": "waiting_input",
                "safe_to_report_success": False,
                "source": "runtime_truth_engine",
            },
            "runtime_contracts": {
                "contract_type": "shell_execution",
                "operation_type": "test_run",
                "runtime_profile": "shell",
                "requested_actions": ["run_command"],
                "capabilities_required": ["shell"],
            },
            "events": [
                {"sequence": 1, "event_type": "run_created"},
                {"sequence": 2, "event_type": "approval_required"},
            ],
        }
    )
    expected = ExpectedRuntimeContract(
        completion={"status": "waiting_input", "safe_to_report_success": False},
        speaker_truth={"runtime_status": "waiting_input", "safe_to_report_success": False},
        contracts={"contract_type": "shell_execution", "requested_actions": ["run_command"]},
        timeline=[{"sequence": 1}],
    )

    report = RuntimeOperatorDoctorService().analyze(snapshot, expected)

    assert report.status == "passed"
    assert report.findings == []
    assert report.matrix.status_for("Completion") == "PASS"
    assert report.matrix.status_for("SpeakerTruth") == "PASS"
    assert report.matrix.status_for("Contracts") == "PASS"
    assert report.matrix.status_for("Timeline") == "PASS"


def test_runtime_explainer_does_not_decide_or_generate_patch():
    snapshot = RuntimeOperatorService().snapshot(runtime_data=_runtime_data())
    report = RuntimeOperatorDoctorService().analyze(snapshot, ExpectedRuntimeContract(intent="workspace_analysis_readonly"))

    explanation = RuntimeExplainerService().explain(report, snapshot=snapshot)

    assert explanation.decision_made is False
    assert explanation.patch_generated is False
    assert explanation.read_only is True
    assert explanation.side_effects is False
    assert explanation.regressions


def test_runtime_patch_planner_only_returns_plan():
    snapshot = RuntimeOperatorService().snapshot(runtime_data=_runtime_data())
    report = RuntimeOperatorDoctorService().analyze(snapshot, ExpectedRuntimeContract(intent="workspace_analysis_readonly"))

    plan = RuntimePatchPlannerService().plan(report, source_hints=["src/aipinho/services/runtime"])

    assert plan.applies_patch is False
    assert plan.read_only is True
    assert plan.side_effects is False
    assert plan.affected_modules
    assert plan.items
    assert "tests/unit/test_runtime_operator_ro.py" in plan.tests


def test_runtime_doctor_rd_domains_include_contracts_timeline_executor_models_tools_skills():
    snapshot = RuntimeOperatorService().snapshot(runtime_data=_runtime_data())
    expected = ExpectedRuntimeContract(
        contracts={"version": "2.0"},
        timeline=[{"sequence": 1, "event_type": "task_created"}],
        executor="not_started",
        models={"SemanticUnderstanding": "qwen"},
        tools=[],
        skills=[],
    )

    report = RuntimeOperatorDoctorService().analyze(snapshot, expected)

    assert report.status == "passed"
    assert report.matrix.status_for("Contracts") == "PASS"
    assert report.matrix.status_for("Timeline") == "PASS"
    assert report.matrix.status_for("Executor") == "PASS"
    assert report.matrix.status_for("Models") == "PASS"
    assert report.matrix.status_for("Tools") == "PASS"
    assert report.matrix.status_for("Skills") == "PASS"


def test_firetest_doctor_runs_doctor_matrix_and_patch_plan_without_side_effects():
    result = FireTestDoctorService().analyze(
        {"runtime_data": _runtime_data()},
        ExpectedRuntimeContract(intent="workspace_analysis_readonly", lifecycle="COMPLETED"),
        source_hints=["src/aipinho/services/runtime"],
    )

    assert result.read_only is True
    assert result.side_effects is False
    assert result.doctor_report.status == "regressions_found"
    assert result.regression_matrix.status_for("Intent") == "FAIL"
    assert result.patch_plan.applies_patch is False
    assert result.patch_plan.affected_modules


def test_runtime_operator_router_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    status_response = client.get("/api/v1/runtime/operator/status")
    assert status_response.status_code == 200
    assert status_response.json()["read_only"] is True

    doctor_status_response = client.get("/api/v1/runtime/doctor")
    assert doctor_status_response.status_code == 200
    assert doctor_status_response.json()["read_only"] is True

    snapshot_response = client.post("/api/v1/runtime/operator/snapshot", json={"runtime_data": _runtime_data()})
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["task_run_id"] == "run_1"

    analyze_response = client.post(
        "/api/v1/runtime/doctor/analyze",
        json={
            "snapshot": snapshot_payload,
            "expected": {"intent": "workspace_analysis_readonly"},
        },
    )
    assert analyze_response.status_code == 200
    assert analyze_response.json()["status"] == "regressions_found"

    firetest_response = client.post(
        "/api/v1/runtime/firetest/analyze",
        json={
            "raw": {"runtime_data": _runtime_data()},
            "expected": {"intent": "workspace_analysis_readonly"},
        },
    )
    assert firetest_response.status_code == 200
    assert firetest_response.json()["patch_plan"]["applies_patch"] is False
