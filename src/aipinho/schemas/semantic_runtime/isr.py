from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ISRStatus = Literal["ready", "disabled", "blocked"]


class ISREntity(AIpinhoModel):
    entity_type: str
    value: str
    confidence: float = 0.0
    source: str = "semantic_interpreter"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ISRMetadata(AIpinhoModel):
    isr_id: str = Field(default_factory=lambda: f"isr_{uuid4().hex}")
    schema_name: str = "IntermediateSemanticRepresentation"
    producer_role: str = "semantic_interpreter"
    capability_id: str = "semantic_understanding"
    contract_id: str | None = None
    session_id: str | None = None
    model_selection: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IntermediateSemanticRepresentation(AIpinhoModel):
    version: str = "1.0"
    status: ISRStatus = "ready"
    intent: str = "unknown"
    entities: list[ISREntity] = Field(default_factory=list)
    scope: str = "unknown"
    permissions_requested: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    ambiguity: dict[str, Any] = Field(default_factory=lambda: {"score": 1.0, "reasons": []})
    confidence: float = 0.0
    semantic_trace: list[dict[str, Any]] = Field(default_factory=list)
    metadata: ISRMetadata = Field(default_factory=ISRMetadata)
    reasoning_summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    effect_flags: dict[str, bool] = Field(
        default_factory=lambda: {
            "side_effects": False,
            "created_contract": False,
            "runtime_executed": False,
            "tools_called": False,
            "skills_called": False,
            "files_written": False,
            "patches_created": False,
        }
    )
    runtime_refs: dict[str, str | None] = Field(default_factory=lambda: {"task_id": None, "approval_id": None})
    extensions: dict[str, Any] = Field(default_factory=dict)

    @property
    def isr_id(self) -> str:
        return self.metadata.isr_id

    @property
    def contract_id(self) -> str | None:
        return self.metadata.contract_id

    @property
    def role_id(self) -> str:
        return self.metadata.producer_role

    @property
    def capability_id(self) -> str:
        return self.metadata.capability_id

    @property
    def model_selection(self) -> dict[str, Any]:
        return self.metadata.model_selection

    @property
    def requested_outputs(self) -> list[str]:
        return self.expected_outputs

    @property
    def ambiguity_score(self) -> float:
        value = self.ambiguity.get("score", 1.0)
        return float(value) if isinstance(value, (int, float)) else 1.0

    @property
    def trace(self) -> list[dict[str, Any]]:
        return self.semantic_trace

    @property
    def side_effects(self) -> bool:
        return bool(self.effect_flags.get("side_effects", False))

    @property
    def created_contract(self) -> bool:
        return bool(self.effect_flags.get("created_contract", False))

    @property
    def runtime_executed(self) -> bool:
        return bool(self.effect_flags.get("runtime_executed", False))

    @property
    def tools_called(self) -> bool:
        return bool(self.effect_flags.get("tools_called", False))

    @property
    def skills_called(self) -> bool:
        return bool(self.effect_flags.get("skills_called", False))

    @property
    def files_written(self) -> bool:
        return bool(self.effect_flags.get("files_written", False))

    @property
    def patches_created(self) -> bool:
        return bool(self.effect_flags.get("patches_created", False))

    @property
    def task_id(self) -> str | None:
        return self.runtime_refs.get("task_id")

    @property
    def approval_id(self) -> str | None:
        return self.runtime_refs.get("approval_id")


class ISRValidationResult(AIpinhoModel):
    status: Literal["passed", "failed"] = "passed"
    version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ISRVersioning(AIpinhoModel):
    current_version: str = "1.0"
    supported_versions: list[str] = Field(default_factory=lambda: ["1.0"])
    backward_compatible_versions: list[str] = Field(default_factory=lambda: ["1.0"])


class ISRSerializer:
    @staticmethod
    def to_dict(isr: IntermediateSemanticRepresentation) -> dict[str, Any]:
        return isr.model_dump(mode="json")

    @staticmethod
    def to_json(isr: IntermediateSemanticRepresentation) -> str:
        return json.dumps(ISRSerializer.to_dict(isr), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> IntermediateSemanticRepresentation:
        return IntermediateSemanticRepresentation.model_validate(data)

    @staticmethod
    def from_json(payload: str) -> IntermediateSemanticRepresentation:
        return IntermediateSemanticRepresentation.model_validate_json(payload)


class ISRValidator:
    def __init__(self, versioning: ISRVersioning | None = None) -> None:
        self.versioning = versioning or ISRVersioning()

    def validate(self, isr: IntermediateSemanticRepresentation | dict[str, Any]) -> ISRValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        parsed: IntermediateSemanticRepresentation
        try:
            parsed = isr if isinstance(isr, IntermediateSemanticRepresentation) else IntermediateSemanticRepresentation.model_validate(isr)
        except Exception as exc:
            return ISRValidationResult(status="failed", errors=[f"isr_structure_invalid:{str(exc)[:200]}"])
        if parsed.version not in self.versioning.supported_versions:
            errors.append("unsupported_isr_version")
        if not parsed.intent:
            errors.append("missing_intent")
        if not parsed.scope:
            errors.append("missing_scope")
        if not 0.0 <= parsed.confidence <= 1.0:
            errors.append("confidence_out_of_range")
        if not isinstance(parsed.ambiguity.get("score", None), (int, float)):
            errors.append("ambiguity_score_missing")
        if not parsed.semantic_trace:
            warnings.append("semantic_trace_empty")
        if any(parsed.effect_flags.values()):
            errors.append("isr_must_not_have_side_effects")
        if parsed.runtime_refs.get("task_id") or parsed.runtime_refs.get("approval_id"):
            errors.append("isr_must_not_reference_runtime_execution")
        return ISRValidationResult(
            status="failed" if errors else "passed",
            version=parsed.version,
            warnings=warnings,
            errors=errors,
        )
