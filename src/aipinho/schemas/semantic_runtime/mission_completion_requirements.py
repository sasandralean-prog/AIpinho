from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


MissionRequirementKind = Literal["completion", "validation"]
MissionRequirementResolutionStatus = Literal[
    "not_applicable",
    "resolved",
    "unavailable",
    "invalid",
]


class MissionCompletionRequirementEvidence(AIpinhoModel):
    kind: MissionRequirementKind
    requirement: str
    evidence_excerpt: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    segment_index: int = Field(ge=0)


class MissionCompletionRequirementResolution(AIpinhoModel):
    status: MissionRequirementResolutionStatus
    reason_code: str
    completion_requirements: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    allow_limited_completion: bool = False
    evidence: list[MissionCompletionRequirementEvidence] = Field(
        default_factory=list
    )
    provenance: dict[str, Any] = Field(default_factory=dict)
