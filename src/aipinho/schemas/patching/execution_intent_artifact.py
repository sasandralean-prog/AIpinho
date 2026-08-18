from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ExecutionArtifactStatus = Literal["complete", "partial", "missing", "invalid"]


class ExecutionIntentArtifact(AIpinhoModel):
    intent_id: str = Field(default_factory=lambda: f"execution_intent_{uuid4().hex}")
    proposal_id: str = ""
    patch_plan_id: str = ""
    workspace: str = ""
    semantic_goal: str = ""
    operation_kind: str = "patch_request"
    target_files: list[str] = Field(default_factory=list)
    target_symbols: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    risk_level: str = ""
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    completeness: float = 0.0
    status: ExecutionArtifactStatus = "missing"


class ExecutableChangeUnit(AIpinhoModel):
    unit_id: str = Field(default_factory=lambda: f"change_unit_{uuid4().hex}")
    target_file: str = ""
    target_symbol: str = ""
    operation: str = "apply_patch_after_approval"
    order_index: int = 0
    depends_on: list[str] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    rollback_strategy: str = ""
    hunk_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class ExecutablePlanArtifact(AIpinhoModel):
    executable_plan_id: str = Field(default_factory=lambda: f"executable_patch_plan_{uuid4().hex}")
    execution_intent_id: str = ""
    patch_plan_id: str = ""
    workspace: str = ""
    target_paths: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    change_units: list[ExecutableChangeUnit] = Field(default_factory=list)
    validation_steps: list[str] = Field(default_factory=list)
    rollback_strategy: dict[str, object] = Field(default_factory=dict)
    checkpoints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    completeness: float = 0.0
    status: ExecutionArtifactStatus = "missing"


class ExecutionPreviewArtifact(AIpinhoModel):
    execution_preview_id: str = Field(default_factory=lambda: f"execution_preview_{uuid4().hex}")
    executable_plan_id: str = ""
    execution_intent_id: str = ""
    patch_plan_id: str = ""
    operation_kind: str = "patch_request"
    target_paths: list[str] = Field(default_factory=list)
    operations: list[str] = Field(default_factory=list)
    change_summary: list[str] = Field(default_factory=list)
    risk_summary: list[str] = Field(default_factory=list)
    rollback_summary: list[str] = Field(default_factory=list)
    impact_summary: list[str] = Field(default_factory=list)
    dependency_summary: list[str] = Field(default_factory=list)
    validation_summary: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    completeness: float = 0.0
    status: ExecutionArtifactStatus = "missing"
