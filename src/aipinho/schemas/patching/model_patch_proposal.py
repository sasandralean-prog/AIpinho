from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.repair_proposal_artifact import RepairProposalArtifact


class ModelPatchEdit(AIpinhoModel):
    path: str
    replacement: str
    rationale: str
    evidence_excerpt: str = ""


class ModelPatchProposal(AIpinhoModel):
    edits: list[ModelPatchEdit] = Field(default_factory=list)


class ModelReplacementProposal(AIpinhoModel):
    replacement: str = ""
    patch_snippet: str = ""
    rationale: str = ""
    confidence: float = 0.0


class ModelAssistedPatchPlanRequest(AIpinhoModel):
    workspace: str
    objective: str
    source_id: str | None = None
    file_context_bundle: dict[str, Any] | None = None
    include_trace: bool = False


class ModelPatchPlanningResult(AIpinhoModel):
    status: str
    plan: PatchPlan | None = None
    repair_proposal: RepairProposalArtifact | None = None
    model_run_id: str | None = None
    model_id: str | None = None
    provider_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
