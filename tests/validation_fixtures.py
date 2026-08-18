from __future__ import annotations

from copy import deepcopy


def valid_evidence(evidence_id="ev1"):
    return {"evidence_id": evidence_id, "source_type": "file", "path": "src/app.py", "line_start": 1, "line_end": 2, "excerpt": "def app(): pass", "confidence": 0.9, "notes": []}


def valid_finding(evidence_id="ev1", severity="medium"):
    return {"finding_id": "finding_1", "title": "Config detected", "category": "service", "severity": severity, "confidence": 0.9, "summary": "Service file observed.", "evidence": [valid_evidence(evidence_id)], "inference": "Evidence supports claim.", "recommendation": "Keep this covered by tests.", "requires_write": False, "requires_followup": False, "trace": []}


def valid_report(status="completed"):
    return {"report_id": "project_report_test", "workspace": "C:/Dev/AIpinho", "goal": "test", "status": status, "generated_at": "2026-06-07T00:00:00+00:00", "executive_summary": "Evidence-cited report.", "sections": [], "findings": [valid_finding()], "recommendations": [{"recommendation_id": "rec1", "title": "Test", "summary": "Add tests", "priority": "medium", "evidence": [valid_evidence()], "requires_write": False}], "limitations": ["partial context"] if status == "partial" else [], "evidence_index": [valid_evidence()], "warnings": [], "trace": []}


def report_missing_evidence():
    report = valid_report()
    report["findings"][0]["evidence"] = []
    report["evidence_index"] = []
    return report


def valid_task_run(status="completed"):
    step_status = "completed" if status == "completed" else "partial"
    return {"run_id": "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "task_id": "task_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "operation_id": "op_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "task_run_id": "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bootstrap_context": {"task_id": "task_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "operation_id": "op_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "task_run_id": "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "runtime_profile": "readonly_analysis", "workspace": "C:/Dev/AIpinho", "contract_type": "readonly_analysis", "context": {"requires_task": True, "bootstrap_invariant": "execution_requires_universal_task"}}, "source_type": "direct", "session_id": "session", "workspace": "C:/Dev/AIpinho", "contract_type": "readonly_analysis", "requested_actions": [], "intent_map": {"intent_type": "readonly_analysis"}, "status": status, "mode": "read_only", "plan": {"plan_id": "plan", "contract_type": "readonly_analysis", "status": "ready", "steps": [{"step_id": "step_01", "step_type": "validate_runtime", "action": "validate_runtime", "required": True, "side_effect": False, "status": step_status, "warnings": [], "violations": [], "output_summary": {}}], "blocked_reasons": [], "trace": []}, "policy_snapshot": {"status": "allowed", "allowed_actions": [], "denied_actions": [], "approval_required_for": []}, "workspace_snapshot": {"blocked": False, "needs_clarification": False, "workspace_path": "C:/Dev/AIpinho"}, "approval_snapshot": {}, "warnings": [], "blocked_reasons": [], "trace": []}


def valid_task_result(status="completed"):
    return {"run_id": "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "status": status, "summary": "Done", "outputs": {"project_report": {"status": "ok"}}, "step_summaries": [], "limitations": ["budget limit"] if status == "partial" else [], "blocked_items": [], "warnings": [], "events_count": 3, "trace_ref": "task-runs/x/trace", "safe_to_display": True}


def valid_events():
    return [{"type": "run_created", "status": "created", "sequence": 1}, {"type": "step_started", "status": "running", "sequence": 2, "step_id": "step_01"}, {"type": "step_completed", "status": "completed", "sequence": 3, "step_id": "step_01"}, {"type": "run_completed", "status": "completed", "sequence": 4}]


def valid_role_pipeline_run():
    return {"run_id": "role_pipeline_run_test", "pipeline_id": "readonly_project_report", "status": "completed", "input_summary": {}, "passes": [{"pass_id": "pass_1", "role_id": "validator", "required": True, "status": "completed", "evaluation_result": {"status": "accepted"}, "model_response": {"real_inference": False}, "warnings": [], "trace": []}], "final_output": {"side_effects": False, "real_inference": False, "tools": False, "write": False, "patch": False}, "warnings": [], "trace": [], "started_at": "2026-06-07T00:00:00+00:00", "finished_at": "2026-06-07T00:00:01+00:00"}
