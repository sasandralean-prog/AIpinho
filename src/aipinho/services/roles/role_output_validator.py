from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_output_contract import RoleOutputContract
from aipinho.schemas.roles.role_pass_output import RolePassOutput
from aipinho.services.evaluation.output_contract_validator import OutputContractValidator
from aipinho.services.evaluation.safety_envelope_validator import SafetyEnvelopeValidator
from aipinho.utils.yaml_loader import load_yaml_file


class RoleOutputValidator:
    def __init__(self, config_path: Path | None = None, output_validator: OutputContractValidator | None = None, safety_validator: SafetyEnvelopeValidator | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_output_contracts.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.output_validator = output_validator or OutputContractValidator()
        self.safety_validator = safety_validator or SafetyEnvelopeValidator()

    def contract_for(self, role_id: str, fallback_contract: str = "plain_text") -> RoleOutputContract:
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        raw = contracts.get(role_id, {}) if isinstance(contracts.get(role_id, {}), dict) else {}
        return RoleOutputContract(role_id=role_id, output_contract_type=str(raw.get("output_contract_type", fallback_contract)), require_evidence=bool(raw.get("require_evidence", False)), reject_without_evidence=bool(raw.get("reject_without_evidence", False)), required_sections=[str(item) for item in raw.get("required_sections", []) or []], deterministic_only=bool(raw.get("deterministic_only", False)))

    def validate(self, output: RolePassOutput, *, output_contract: dict[str, Any], safety_envelope: dict[str, Any], evidence: list[dict[str, object]] | None = None, policy_decision: dict[str, Any] | None = None) -> dict[str, object]:
        evidence = evidence or []
        contract = self.contract_for(output.role_id, str(output_contract.get("contract_type", "plain_text")))
        violations: list[str] = []
        warnings: list[str] = []
        content = output.content or ""
        if len(content) > contract.max_output_chars:
            violations.append("role_output_too_large")
        if contract.require_evidence and contract.reject_without_evidence and not evidence:
            violations.append("missing_evidence")
        contract_payload = {**output_contract, "contract_type": contract.output_contract_type}
        if contract.required_sections:
            contract_payload["required_sections"] = contract.required_sections
        contract_result = self.output_validator.validate(content, contract_payload)
        violations.extend(contract_result.violations)
        warnings.extend(contract_result.warnings)
        safety_result = self.safety_validator.validate(content, safety_envelope, policy_decision or {})
        violations.extend([str(item.get("violation_id", item.get("type", "safety_violation"))) for item in safety_result.get("violations", [])])
        warnings.extend([str(item) for item in safety_result.get("warnings", [])])
        if any(term in content.lower() for term in ["executei comando", "apliquei patch", "salvei arquivo", "modifiquei arquivo"]):
            violations.append("forbidden_side_effect_claim")
        violations = list(dict.fromkeys(violations))
        return {"valid": not violations and contract_result.valid and bool(safety_result.get("valid", True)), "violations": violations, "warnings": list(dict.fromkeys(warnings)), "contract": contract.model_dump()}

    def status(self) -> dict[str, object]:
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        return {"status": "ok", "service": "role_output_validator", "contracts": sorted(contracts.keys())}
