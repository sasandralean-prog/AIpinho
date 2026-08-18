from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact
from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_risk import PatchRiskAssessment
from aipinho.schemas.patching.repair_proposal_artifact import RepairProposalArtifact
from aipinho.schemas.patching.patch_validation import PatchValidationResult
from aipinho.schemas.patching.rollback_note import RollbackNote
from aipinho.schemas.patching.test_recommendation import TestRecommendation


class PatchPlan(AIpinhoModel):
    plan_id: str
    status: str
    workspace: str
    source_type: str = "user_request"
    source_id: str | None = None
    objective: str = ""
    affected_files: list[AffectedFile] = Field(default_factory=list)
    diagnosis_artifacts: list[CanonicalDiagnosisArtifact] = Field(default_factory=list)
    patch_candidates: list[PatchCandidateArtifact] = Field(default_factory=list)
    evidence: list[PatchEvidence] = Field(default_factory=list)
    hunks: list[PatchHunk] = Field(default_factory=list)
    diff_proposal: DiffProposal | None = None
    repair_proposal: RepairProposalArtifact | None = None
    risk: PatchRiskAssessment = Field(default_factory=PatchRiskAssessment)
    validation: PatchValidationResult = Field(default_factory=PatchValidationResult)
    rollback_notes: list[RollbackNote] = Field(default_factory=list)
    test_recommendations: list[TestRecommendation] = Field(default_factory=list)
    quality_gate: dict[str, object] = Field(default_factory=dict)
    apply_enabled: bool = False
    write_enabled: bool = False
    safe_to_apply: bool = False
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
