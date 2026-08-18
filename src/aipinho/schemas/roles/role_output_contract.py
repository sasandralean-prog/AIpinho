from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class RoleOutputContract(AIpinhoModel):
    role_id: str
    output_contract_type: str = "plain_text"
    require_evidence: bool = False
    reject_without_evidence: bool = False
    required_sections: list[str] = Field(default_factory=list)
    deterministic_only: bool = False
    max_output_chars: int = 8000
