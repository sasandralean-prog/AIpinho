from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_evidence import PatchEvidence


class PatchPlanRequest(AIpinhoModel):
    workspace: str
    source_type: str = "user_request"
    source_id: str | None = None
    objective: str = ""
    affected_files: list[str] = Field(default_factory=list)
    diagnosis_artifacts: list[CanonicalDiagnosisArtifact] = Field(default_factory=list)
    patch_candidates: list[PatchCandidateArtifact] = Field(default_factory=list)
    evidence: list[PatchEvidence] = Field(default_factory=list)
    replacements: dict[str, str] = Field(default_factory=dict)
    model_assisted: bool = False
    include_trace: bool = False
