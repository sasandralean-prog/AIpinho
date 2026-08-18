from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding

class TaskResultValidator:
    def validate(self, result: Any, *, run: Any | None = None) -> list:
        data = as_dict(result)
        findings = []
        if not data:
            findings.append(finding("missing_task_result", "Missing TaskRunResult", "TaskRun requires a persisted result before it can pass validation.", severity="error", validator="task_result", blocking=True))
            return findings
        if data.get("safe_to_display") is False:
            findings.append(finding("unsafe_result_display", "Unsafe result", "TaskRunResult marked safe_to_display=false.", severity="error", validator="task_result", blocking=True))
        if data.get("status") == "partial" and not data.get("limitations"):
            findings.append(finding("missing_limitations_when_partial", "Partial result missing limitations", "Partial TaskRunResult must explain limitations.", severity="error", validator="task_result", blocking=True))
        if data.get("status") == "completed" and data.get("limitations"):
            findings.append(finding("status_inconsistency", "Completed with limitations", "Completed result contains limitations and should be partial or passed_with_warnings.", severity="warning", validator="task_result", evidence=list(data.get("limitations") or [])))
        if not data.get("summary"):
            findings.append(finding("empty_output", "Empty result summary", "TaskRunResult summary is empty.", severity="error", validator="task_result", blocking=True))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_result_validator"}
