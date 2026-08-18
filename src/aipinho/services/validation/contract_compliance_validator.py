from __future__ import annotations
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.services.validation.validation_common import as_dict, finding
from aipinho.utils.yaml_loader import load_yaml_file

class ContractComplianceValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "validation" / "contract_compliance_policy.yaml", critical=True, root=PATHS.config_root / "validation")

    def validate(self, payload: Any) -> list:
        data = as_dict(payload)
        findings = []
        contract_type = data.get("contract_type") or data.get("contract", {}).get("contract_type") if isinstance(data.get("contract"), dict) else data.get("contract_type")
        if not contract_type:
            findings.append(finding("missing_contract_type", "Missing contract type", "Validation target does not expose contract_type.", severity="error", validator="contract_compliance", blocking=True))
        policy_snapshot = data.get("policy_snapshot") or data.get("policy_decision") or {}
        requested = set(data.get("requested_actions") or [])
        allowed = set(policy_snapshot.get("allowed_actions") or []) if isinstance(policy_snapshot, dict) else set()
        denied = set(policy_snapshot.get("denied_actions") or []) if isinstance(policy_snapshot, dict) else set()
        approval_required = set(policy_snapshot.get("approval_required_for") or []) if isinstance(policy_snapshot, dict) else set()
        approval_id = data.get("approval_id")
        effective_allowed = allowed | (approval_required if approval_id else set())
        if requested and effective_allowed and not requested.issubset(effective_allowed):
            findings.append(finding("action_outside_contract", "Action outside contract", "Requested actions are not covered by allowed or explicitly approved policy actions.", severity="error", validator="contract_compliance", evidence=sorted(requested - effective_allowed), blocking=True))
        if requested.intersection(denied):
            findings.append(finding("denied_action_requested", "Denied action requested", "A denied action appears in requested actions.", severity="critical", validator="contract_compliance", evidence=sorted(requested.intersection(denied)), blocking=True))
        if approval_required.intersection(requested) and not approval_id:
            findings.append(finding("approval_required_missing", "Approval required", "A requested action requires approval but no approval_id was recorded.", severity="error", validator="contract_compliance", evidence=sorted(approval_required.intersection(requested)), blocking=True))
        contract_cfg = (self.policy.get("contract_types", {}) or {}).get(str(contract_type), {}) if contract_type else {}
        forbidden = set(contract_cfg.get("forbidden_actions", []) or []) if isinstance(contract_cfg, dict) else set()
        if requested.intersection(forbidden):
            findings.append(finding("forbidden_contract_action", "Forbidden contract action", "Requested action is forbidden by contract type.", severity="critical", validator="contract_compliance", evidence=sorted(requested.intersection(forbidden)), blocking=True))
        outputs = set((data.get("result") or {}).get("outputs", {}).keys()) if isinstance(data.get("result"), dict) else set(data.get("outputs", {}).keys()) if isinstance(data.get("outputs"), dict) else set()
        allowed_outputs = set(contract_cfg.get("allowed_result_outputs", []) or []) if isinstance(contract_cfg, dict) else set()
        if outputs and allowed_outputs and not outputs.issubset(allowed_outputs):
            findings.append(finding("output_outside_contract", "Output outside contract", "Result contains output group outside contract.", severity="warning", validator="contract_compliance", evidence=sorted(outputs - allowed_outputs)))
        return findings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "contract_compliance_validator"}
