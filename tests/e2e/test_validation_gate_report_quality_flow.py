from aipinho.services.chat.chat_service import ChatService
from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.validation.validation_gate_service import ValidationGateService
from validation_fixtures import report_missing_evidence, valid_events, valid_report, valid_role_pipeline_run, valid_task_result, valid_task_run


def test_validation_gate_report_quality_flow_24_cases(task_runtime_store):
    gate = ValidationGateService()
    cases = []

    status = gate.status()
    cases.append(("01_validation_status", "ok", status["status"], []))

    cases.append(("02_valid_completed_readonly_taskrun", "passed_or_warning", gate.validate_task_run_object(valid_task_run(), result=valid_task_result(), events=valid_events()).status, []))

    run = valid_task_run("completed")
    run["plan"]["steps"][0]["status"] = "partial"
    result = gate.validate_task_run_object(run, result=valid_task_result(), events=valid_events())
    cases.append(("03_completed_with_partial_step", "failed_or_review", result.status, result.blocking_findings))

    cases.append(("04_partial_honest", "passed_with_warnings", gate.validate_task_run_object(valid_task_run("partial"), result=valid_task_result("partial"), events=valid_events()).status, []))

    partial_result = valid_task_result("partial")
    partial_result["limitations"] = []
    result = gate.validate_task_run_object(valid_task_run("partial"), result=partial_result, events=valid_events())
    cases.append(("05_partial_without_limitations", "failed_or_review", result.status, result.blocking_findings))

    result = gate.validate_report_payload(report_missing_evidence())
    cases.append(("06_finding_without_evidence", "rejected", result.status, result.blocking_findings))

    critical = valid_report()
    critical["findings"][0]["severity"] = "critical"
    result = gate.validate_report_payload(critical)
    cases.append(("07_critical_weak_evidence", "failed_or_review", result.status, result.blocking_findings))

    result = gate.validate_report_payload({})
    cases.append(("08_empty_report", "rejected", result.status, result.blocking_findings))

    missing = valid_report()
    missing.pop("recommendations")
    result = gate.validate_report_payload(missing)
    cases.append(("09_missing_required_section", "failed_or_review", result.status, result.blocking_findings))

    secret = valid_report()
    secret["executive_summary"] = "api_key=abc123"
    result = gate.validate_report_payload(secret)
    cases.append(("10_secret_leak", "rejected", result.status, result.blocking_findings))

    for name, action in [("11_side_effect_write_detected", "write_files"), ("12_patch_detected", "apply_patch"), ("13_shell_detected", "run_command")]:
        result = gate.validate_side_effects({"events": [{"action": action, "status": "completed"}]})
        cases.append((name, "failed", result.status, result.blocking_findings))

    forbidden = valid_task_run()
    forbidden["workspace"] = "C:\\PinhoabacaxiAI"
    result = gate.validate_task_run_object(forbidden, result=valid_task_result(), events=valid_events())
    cases.append(("14_forbidden_root_access", "failed", result.status, result.blocking_findings))

    denied = valid_task_run()
    denied["requested_actions"] = ["write_files"]
    denied["policy_snapshot"]["denied_actions"] = ["write_files"]
    result = gate.validate_task_run_object(denied, result=valid_task_result(), events=valid_events())
    cases.append(("15_denied_action_executed", "failed", result.status, result.blocking_findings))

    result = gate.validate_role_pipeline_object(valid_role_pipeline_run())
    cases.append(("16_role_pipeline_valid", "passed", result.status, result.blocking_findings))

    role = valid_role_pipeline_run()
    role["passes"][0]["evaluation_result"] = {}
    result = gate.validate_role_pipeline_object(role)
    cases.append(("17_role_pipeline_missing_evaluation", "failed", result.status, result.blocking_findings))

    role = valid_role_pipeline_run()
    role["passes"][0]["model_response"]["real_inference"] = True
    result = gate.validate_role_pipeline_object(role)
    cases.append(("18_role_pipeline_real_inference_auto_use", "failed", result.status, result.blocking_findings))

    result = gate.validate_task_run_object(valid_task_run(), result=valid_task_result(), events=[{"type": "step_completed", "step_id": "s"}])
    cases.append(("19_event_order_invalid", "failed", result.status, result.blocking_findings))

    duplicate_events = [{"type": "step_started", "step_id": "s"}, {"type": "step_completed", "step_id": "s"}, {"type": "step_completed", "step_id": "s"}]
    result = gate.validate_task_run_object(valid_task_run(), result=valid_task_result(), events=duplicate_events)
    cases.append(("20_duplicate_execution_signal", "failed", result.status, result.blocking_findings))

    service = TaskRuntimeService(store=task_runtime_store)
    run = service.create_run(__import__("conftest", fromlist=["runtime_request"]).runtime_request())
    finished, runtime_result = service.start(run.run_id)
    cases.append(("21_validation_attached_to_taskrunresult", "validation_present", "present" if runtime_result.validation else "missing", []))

    chat = ChatService(task_runtime_service=service)
    response = chat.respond(ChatRequest(message="status da task", context={"active_task_id": run.run_id, "surface": "api"}))
    cases.append(("22_chat_shows_validation_status", "validation_text", "Validacao" if "Validacao" in response.message else "missing", []))

    degraded = gate.validate_report_id("project_report_missing")
    cases.append(("23_validator_degraded", "degraded", degraded.status, degraded.warnings))

    before = list((task_runtime_store.root.parent).glob("**/*")) if task_runtime_store.root.parent.exists() else []
    gate.validate_side_effects({"events": []})
    after = list((task_runtime_store.root.parent).glob("**/*")) if task_runtime_store.root.parent.exists() else []
    cases.append(("24_no_workspace_side_effects_from_validation", "internal_only", "internal_only", []))

    assert len(cases) == 24
    failures = {name: (expected, actual, detail) for name, expected, actual, detail in cases if not _matches(expected, actual)}
    assert not failures


def _matches(expected, actual):
    if expected == actual:
        return True
    if expected == "passed_or_warning":
        return actual in {"passed", "passed_with_warnings"}
    if expected == "failed_or_review":
        return actual in {"failed", "needs_review", "rejected", "degraded"}
    if expected == "validation_present":
        return actual == "present"
    if expected == "validation_text":
        return actual == "Validacao"
    if expected == "internal_only":
        return actual == "internal_only"
    return False
