from __future__ import annotations

from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.services.patching.diagnosis_alignment_validator import DiagnosisAlignmentValidator
from aipinho.services.patching.diagnosis_pipeline_compiler import DiagnosisPipelineCompiler
from aipinho.services.patching.diagnosis_quality_analyzer import DiagnosisQualityAnalyzer
from aipinho.services.patching.patch_candidate_actionability_analyzer import PatchCandidateActionabilityAnalyzer
from aipinho.services.patching.patch_candidate_builder import PatchCandidateBuilder
from aipinho.services.patching.patch_candidate_quality_analyzer import PatchCandidateQualityAnalyzer
from aipinho.services.patching.repair_intent_resolver import RepairIntentResolver


class DiagnosisRuntimeService:
    """Canonical translator from technical diagnosis into patch candidates."""

    def __init__(
        self,
        candidate_builder: PatchCandidateBuilder | None = None,
        diagnosis_quality: DiagnosisQualityAnalyzer | None = None,
        candidate_quality: PatchCandidateQualityAnalyzer | None = None,
        actionability: PatchCandidateActionabilityAnalyzer | None = None,
        alignment: DiagnosisAlignmentValidator | None = None,
        repair_intent: RepairIntentResolver | None = None,
        compiler: DiagnosisPipelineCompiler | None = None,
    ) -> None:
        self.candidate_builder = candidate_builder or PatchCandidateBuilder()
        self.diagnosis_quality = diagnosis_quality or DiagnosisQualityAnalyzer()
        self.candidate_quality = candidate_quality or PatchCandidateQualityAnalyzer()
        self.actionability = actionability or PatchCandidateActionabilityAnalyzer()
        self.alignment = alignment or DiagnosisAlignmentValidator()
        self.repair_intent = repair_intent or RepairIntentResolver()
        self.compiler = compiler or DiagnosisPipelineCompiler()

    def enrich_diagnosis(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        current_content_by_path: dict[str, str] | None = None,
    ) -> CanonicalDiagnosisArtifact:
        enriched = self.repair_intent.enrich(diagnosis)
        return self.compiler.enrich_diagnosis(
            enriched,
            current_content_by_path=current_content_by_path,
        )

    def candidates_from_diagnosis(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        current_content_by_path: dict[str, str] | None = None,
    ) -> list[PatchCandidateArtifact]:
        enriched = self.enrich_diagnosis(
            diagnosis,
            current_content_by_path=current_content_by_path,
        )
        diagnosis_quality = self.diagnosis_quality.analyze(enriched)
        candidates = self.candidate_builder.from_diagnosis(
            enriched,
            current_content_by_path=current_content_by_path,
        )
        for candidate in candidates:
            candidate_quality = self.candidate_quality.analyze(candidate)
            actionability = self.actionability.analyze(candidate)
            candidate_transformation = self.compiler.candidate_transformation(
                candidate,
                repair_task=actionability.repair_task,
            )
            candidate.candidate_transformation = candidate_transformation
            candidate.technical_context = {
                **dict(candidate.technical_context),
                "diagnosis_quality": diagnosis_quality.model_dump(mode="json"),
                "patch_candidate_quality": candidate_quality.model_dump(mode="json"),
                "actionability": actionability.model_dump(mode="json"),
                "repair_task": actionability.repair_task.model_dump(mode="json"),
                "repair_intent": enriched.repair_intent.model_dump(mode="json") if enriched.repair_intent else None,
                "semantic_evidence": enriched.semantic_evidence.model_dump(mode="json") if enriched.semantic_evidence else None,
                "behavior_localization": enriched.behavior_localization.model_dump(mode="json") if enriched.behavior_localization else None,
                "behavior_justification": enriched.behavior_justification.model_dump(mode="json") if enriched.behavior_justification else None,
                "candidate_transformation": candidate_transformation.model_dump(mode="json"),
            }
            alignment = self.alignment.analyze(candidate)
            candidate.technical_context = {
                **dict(candidate.technical_context),
                "alignment": alignment.model_dump(mode="json"),
            }
        return candidates

    def enrich_actionability(
        self,
        candidate: PatchCandidateArtifact,
        *,
        policy: dict[str, object] | None = None,
    ):
        actionability = self.actionability.analyze(candidate, policy=policy)
        candidate_transformation = self.compiler.candidate_transformation(
            candidate,
            repair_task=actionability.repair_task,
        )
        candidate.candidate_transformation = candidate_transformation
        candidate.technical_context = {
            **dict(candidate.technical_context),
            "actionability": actionability.model_dump(mode="json"),
            "repair_task": actionability.repair_task.model_dump(mode="json"),
            "candidate_transformation": candidate_transformation.model_dump(mode="json"),
        }
        alignment = self.alignment.analyze(candidate)
        candidate.technical_context = {
            **dict(candidate.technical_context),
            "alignment": alignment.model_dump(mode="json"),
        }
        return actionability

    def alignment_for_candidate(self, candidate: PatchCandidateArtifact):
        alignment = self.alignment.analyze(candidate)
        candidate.technical_context = {
            **dict(candidate.technical_context),
            "alignment": alignment.model_dump(mode="json"),
        }
        return alignment

    def candidates_from_diagnoses(
        self,
        diagnoses: list[CanonicalDiagnosisArtifact],
        *,
        current_content_by_path: dict[str, str] | None = None,
    ) -> list[PatchCandidateArtifact]:
        candidates: list[PatchCandidateArtifact] = []
        for diagnosis in diagnoses:
            candidates.extend(
                self.candidates_from_diagnosis(
                    diagnosis,
                    current_content_by_path=current_content_by_path,
                )
            )
        return candidates

    def diagnoses_from_request(
        self,
        *,
        workspace: str,
        objective: str,
        source_type: str,
        source_id: str | None,
        paths: list[str],
        evidence: list[PatchEvidence],
        candidates: list[PatchCandidateArtifact] | None = None,
    ) -> list[CanonicalDiagnosisArtifact]:
        diagnoses = self.candidate_builder.diagnoses_from_request(
            workspace=workspace,
            objective=objective,
            source_type=source_type,
            source_id=source_id,
            paths=paths,
            evidence=evidence,
            candidates=candidates,
        )
        return [self.enrich_diagnosis(diagnosis) for diagnosis in diagnoses]
