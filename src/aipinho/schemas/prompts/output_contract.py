from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class OutputContract(AIpinhoModel):
    contract_type: str
    format: str = "text"
    required_sections: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    require_evidence: bool = False
    require_valid_json: bool = False
    max_chars: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
