from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict
from aipinho.services.validation.contract_compliance_validator import ContractComplianceValidator
from aipinho.services.validation.policy_compliance_validator import PolicyComplianceValidator
from aipinho.services.validation.side_effect_validator import SideEffectValidator
from aipinho.services.validation.task_event_consistency_validator import TaskEventConsistencyValidator
from aipinho.services.validation.task_result_validator import TaskResultValidator
from aipinho.services.validation.task_status_consistency_validator import TaskStatusConsistencyValidator
from aipinho.services.validation.workspace_access_validator import WorkspaceAccessValidator

class TaskRunValidator:
    def __init__(self) -> None:
        self.status_validator = TaskStatusConsistencyValidator()
        self.result_validator = TaskResultValidator()
        self.events_validator = TaskEventConsistencyValidator()
        self.contract_validator = ContractComplianceValidator()
        self.policy_validator = PolicyComplianceValidator()
        self.side_effect_validator = SideEffectValidator()
        self.workspace_validator = WorkspaceAccessValidator()

    def validate(self, run: Any, *, result: Any | None = None, events: Any | None = None) -> list:
        data = as_dict(run)
        result_data = as_dict(result)
        payload = {**data, "result": result_data, "events": [as_dict(item) for item in (events or [])]}
        findings = []
        findings.extend(self.status_validator.validate(data, result_data))
        findings.extend(self.result_validator.validate(result_data, run=data))
        findings.extend(self.events_validator.validate(events or []))
        findings.extend(self.contract_validator.validate(payload))
        findings.extend(self.policy_validator.validate(payload))
        findings.extend(self.side_effect_validator.validate(payload))
        findings.extend(self.workspace_validator.validate(payload))
        return findings

    def status(self): return {"status": "ok", "service": "task_run_validator"}
