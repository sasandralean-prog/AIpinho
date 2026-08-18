from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.evaluation.contract_validation_result import ContractValidationResult
from aipinho.services.evaluation.json_output_validator import JSONOutputValidator
from aipinho.services.evaluation.markdown_output_validator import MarkdownOutputValidator
from aipinho.services.evaluation.text_output_validator import TextOutputValidator
from aipinho.utils.yaml_loader import load_yaml_file


class OutputContractValidator:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "output_contract_validation_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.json_validator = JSONOutputValidator()
        self.markdown_validator = MarkdownOutputValidator()
        self.text_validator = TextOutputValidator()

    def _contract(self, output_contract: dict[str, Any] | None) -> dict[str, Any]:
        contract = dict(output_contract or {})
        contract_type = str(contract.get("contract_type") or contract.get("type") or "plain_text")
        configured = self.config.get("contracts", {}).get(contract_type, {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        merged = {**configured, **contract}
        merged["contract_type"] = contract_type
        if "format" not in merged:
            merged["format"] = "json" if merged.get("require_valid_json") else "markdown" if merged.get("required_sections") else "text"
        return merged

    def validate(self, response_content: str, output_contract: dict[str, Any] | None) -> ContractValidationResult:
        contract = self._contract(output_contract)
        contract_type = str(contract.get("contract_type", "plain_text"))
        expected_format = str(contract.get("format", "text"))
        required_fields = [str(item) for item in contract.get("required_fields", []) or []]
        required_sections = [str(item) for item in contract.get("required_sections", []) or []]
        if contract_type == "chat_response" and bool(contract.get("allow_plain_text_fallback", True)) and response_content.strip():
            return self.text_validator.validate(response_content, contract_type=contract_type)
        if expected_format == "json" or bool(contract.get("require_valid_json")):
            json_policy = self.config.get("formats", {}).get("json", {}) if isinstance(self.config.get("formats", {}), dict) else {}
            result = self.json_validator.validate(
                response_content,
                required_fields=required_fields,
                allow_markdown_fence=bool(json_policy.get("allow_markdown_fence", True)),
                reject_trailing_text=bool(json_policy.get("reject_trailing_text", False)),
                contract_type=contract_type,
            )
            result.required_sections = required_sections
            return result
        if expected_format == "markdown" or required_sections:
            return self.markdown_validator.validate(response_content, required_sections=required_sections, contract_type=contract_type)
        text_policy = self.config.get("formats", {}).get("text", {}) if isinstance(self.config.get("formats", {}), dict) else {}
        return self.text_validator.validate(response_content, contract_type=contract_type, max_empty_ratio=float(text_policy.get("max_empty_ratio", 0.8)))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "output_contract_validator", "enabled": True}
