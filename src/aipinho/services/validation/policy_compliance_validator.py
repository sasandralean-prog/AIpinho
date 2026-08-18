from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding

class PolicyComplianceValidator:
    def validate(self, payload: Any) -> list:
        data = as_dict(payload)
        findings = []
        policy = data.get("policy_snapshot") or data.get("policy_decision") or {}
        if not policy:
            findings.append(finding("missing_policy_snapshot", "Missing policy snapshot", "Output cannot be trusted without policy snapshot.", severity="error", validator="policy_compliance", blocking=True))
            return findings
        status = str(policy.get("status") or policy.get("policy_status") or "") if isinstance(policy, dict) else ""
        if status in {"denied", "blocked"}:
            findings.append(finding("policy_denied_target", "Policy denied target", "Policy snapshot status denies the target.", severity="critical", validator="policy_compliance", evidence=[status], blocking=True))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "policy_compliance_validator"}
