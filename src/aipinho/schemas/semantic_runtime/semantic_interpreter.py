from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity


SemanticInterpreterStatus = Literal["ready", "disabled", "blocked"]


SemanticEntity = ISREntity


class SemanticInterpreterContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"semantic_contract_{uuid4().hex}")
    role_id: str = "semantic_interpreter"
    capability_id: str = "semantic_understanding"
    prompt: str
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(
        default_factory=lambda: [
            "create_contract",
            "create_task",
            "create_approval",
            "call_tool",
            "call_skill",
            "write_file",
            "apply_patch",
            "execute_runtime",
        ]
    )


SemanticInterpreterOutput = IntermediateSemanticRepresentation


class SemanticInterpreterPipelineResult(AIpinhoModel):
    pipeline_id: str = "semantic_interpreter_pipeline"
    status: SemanticInterpreterStatus = "ready"
    contract: SemanticInterpreterContract
    output: SemanticInterpreterOutput
    warnings: list[str] = Field(default_factory=list)
