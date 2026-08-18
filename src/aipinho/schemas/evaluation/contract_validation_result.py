from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ContractValidationResult(AIpinhoModel):
    valid: bool
    format_valid: bool = False
    contract_type: str = "plain_text"
    expected_format: str = "text"
    detected_format: str = "text"
    required_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    parsed_json: dict[str, Any] | list[Any] | None = None
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
