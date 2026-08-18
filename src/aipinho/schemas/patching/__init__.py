from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact, DiagnosisEvidenceRef, DiagnosisMetadata, RepairHint, RepairIntent, TechnicalLocalization
from aipinho.schemas.patching.diagnosis_pipeline_artifact import (
    BehaviorJustificationArtifact,
    BehaviorLocalizationArtifact,
    CandidateTransformationArtifact,
    SemanticEvidenceArtifact,
    SemanticEvidenceEntry,
)
from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.diff_preview import DiffPreview
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest
from aipinho.schemas.patching.patch_plan_result import PatchPlanResult
from aipinho.schemas.patching.model_patch_proposal import ModelAssistedPatchPlanRequest, ModelPatchEdit, ModelPatchPlanningResult, ModelPatchProposal, ModelReplacementProposal
from aipinho.schemas.patching.patch_risk import PatchRiskAssessment
from aipinho.schemas.patching.repair_proposal_artifact import (
    RepairProposalAssembly,
    RepairProposalAssemblyStage,
    RepairProposalArtifact,
    RepairProposalComponent,
    RepairProposalComponents,
    RepairProposalConcreteChange,
    RepairProposalImpact,
    RepairProposalRisks,
    RepairProposalRollback,
    RepairProposalTarget,
)
from aipinho.schemas.patching.execution_intent_artifact import (
    ExecutableChangeUnit,
    ExecutablePlanArtifact,
    ExecutionArtifactStatus,
    ExecutionIntentArtifact,
    ExecutionPreviewArtifact,
)
from aipinho.schemas.patching.patch_status import PatchPlanningStatus
from aipinho.schemas.patching.patch_validation import PatchValidationResult
from aipinho.schemas.patching.rollback_note import RollbackNote
from aipinho.schemas.patching.test_recommendation import TestRecommendation
