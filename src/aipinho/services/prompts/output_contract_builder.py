from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.prompts.output_contract import OutputContract
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.utils.yaml_loader import load_yaml_file


class OutputContractBuilder:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "prompts" / "output_contracts.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def get_contract(self, contract_type: str) -> OutputContract:
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        value = contracts.get(contract_type) or contracts.get("plain_text", {})
        resolved_type = contract_type if contract_type in contracts else "plain_text"
        return OutputContract(
            contract_type=resolved_type,
            format=str(value.get("format", "text")),
            required_sections=list(value.get("required_sections", []) or []),
            required_fields=list(value.get("required_fields", []) or []),
            require_evidence=bool(value.get("require_evidence", False)),
            require_valid_json=bool(value.get("require_valid_json", False)),
            max_chars=value.get("max_chars") if isinstance(value.get("max_chars"), int) else None,
            metadata={
                k: v
                for k, v in value.items()
                if k
                not in {
                    "format",
                    "required_sections",
                    "required_fields",
                    "require_evidence",
                    "require_valid_json",
                    "max_chars",
                }
            },
        )

    def validate_contract(self, contract: OutputContract) -> dict[str, object]:
        if not contract.format:
            return {"valid": False, "error": "contract_format_required"}
        return {"valid": True}

    def build_contract_message(self, contract: OutputContract) -> PromptMessage:
        parts = [f"Output contract: {contract.contract_type}", f"Format: {contract.format}"]
        if contract.required_sections:
            parts.append("Required sections: " + ", ".join(contract.required_sections))
        if contract.required_fields:
            parts.append("Required fields: " + ", ".join(contract.required_fields))
        if contract.require_evidence:
            parts.append("Evidence is required for claims.")
        return PromptMessage(
            role="developer",
            content="\n".join(parts),
            metadata={"contract_type": contract.contract_type},
        )

    def validate_model_response_against_contract(
        self,
        content: str,
        contract: dict[str, Any] | OutputContract,
    ) -> dict[str, object]:
        obj = contract if isinstance(contract, OutputContract) else OutputContract.model_validate(contract) if contract else self.get_contract("plain_text")
        if obj.require_valid_json or obj.format == "json":
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                return {"valid": False, "error": f"invalid_json:{exc.msg}"}
            missing = [field for field in obj.required_fields if field not in parsed]
            return {
                "valid": not missing,
                "error": "missing_required_fields:" + ",".join(missing) if missing else None,
            }
        if obj.contract_type == "chat_response":
            return {"valid": bool(content.strip()), "error": None if content.strip() else "empty_response"}
        if obj.required_sections:
            lowered = content.lower()
            missing = [
                section
                for section in obj.required_sections
                if section.replace("_", " ") not in lowered and section.lower() not in lowered
            ]
            if missing:
                return {"valid": False, "error": "missing_required_sections:" + ",".join(missing)}
        return {"valid": True, "error": None}

    def status(self) -> dict[str, object]:
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        return {"status": "ok", "service": "output_contract_builder", "contracts": sorted(contracts.keys())}
