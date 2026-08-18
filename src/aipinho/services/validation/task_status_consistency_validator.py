from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding

TERMINAL = {"completed", "partial", "failed", "cancelled", "blocked"}

class TaskStatusConsistencyValidator:
    def validate(self, run: Any, result: Any | None = None) -> list:
        data = as_dict(run)
        result_data = as_dict(result)
        findings = []
        status = str(data.get("status") or result_data.get("status") or "")
        if status not in TERMINAL:
            findings.append(finding("non_terminal_task_run", "TaskRun not terminal", "TaskRun must be terminal before final validation passes.", severity="error", validator="task_status_consistency", evidence=[status], blocking=True))
        steps = list(((data.get("plan") or {}).get("steps") or [])) if isinstance(data.get("plan"), dict) else []
        if status == "completed":
            bad = [step for step in steps if step.get("required", True) and step.get("status") != "completed"]
            if bad:
                findings.append(finding("status_inconsistency", "Completed run has incomplete required step", "Completed status requires every required step to be completed.", severity="error", validator="task_status_consistency", evidence=[str(step.get("step_id")) for step in bad], blocking=True))
            if result_data.get("limitations") or data.get("blocked_reasons"):
                findings.append(finding("status_inconsistency", "Completed run has limitations or blocked reasons", "Clean completed status is not honest when limitations or blocked reasons exist.", severity="warning", validator="task_status_consistency"))
        if status == "partial":
            limitations = list(result_data.get("limitations") or []) + list(data.get("warnings") or [])
            if not limitations:
                findings.append(finding("missing_limitations_when_partial", "Partial run missing limitations", "Partial TaskRun requires explicit limitations/warnings.", severity="error", validator="task_status_consistency", blocking=True))
            else:
                findings.append(finding("partial_result", "Partial run with limitations", "Partial TaskRun is honest but still not a fully completed result.", severity="warning", validator="task_status_consistency", evidence=limitations[:5], blocking=False))
        if status == "blocked" and not data.get("blocked_reasons"):
            findings.append(finding("status_inconsistency", "Blocked run missing blocked reasons", "Blocked status requires blocked_reasons.", severity="warning", validator="task_status_consistency"))
        return findings

    def status(self): return {"status": "ok", "service": "task_status_consistency_validator"}
