from __future__ import annotations

from aipinho.schemas.patching.canonical_diagnosis_artifact import (
    CanonicalDiagnosisArtifact,
    DiagnosisEvidenceRef,
    DiagnosisMetadata,
    RepairHint,
    TechnicalLocalization,
)
from aipinho.services.patching.diagnosis_runtime_service import DiagnosisRuntimeService


def test_diagnosis_runtime_is_patch_candidate_boundary():
    diagnosis = CanonicalDiagnosisArtifact(
        metadata=DiagnosisMetadata(source_type="analysis", source_id="analysis_1", task_run_id="run_1"),
        workspace="workspace",
        semantic_goal="Correct observed behavior.",
        observed_behavior="render returns the stale value.",
        expected_behavior="render returns the fresh value.",
        technical_localization=[
            TechnicalLocalization(
                workspace="workspace",
                target_file="src/app.py",
                target_symbol="render",
                symbol_kind="function",
                confidence=0.8,
            )
        ],
        evidence=[DiagnosisEvidenceRef(evidence_id="artifact_1", source_type="artifact")],
        confidence=0.7,
        repair_hints=[RepairHint(strategy="Replace stale branch.", constraints=["replacement_only"])],
    )

    candidates = DiagnosisRuntimeService().candidates_from_diagnosis(
        diagnosis,
        current_content_by_path={"src/app.py": "def render():\n    return 'old'\n"},
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.diagnosis_id == diagnosis.diagnosis_id
    assert candidate.target_file == "src/app.py"
    assert candidate.target_symbol == "render"
    assert candidate.current_content_excerpt
    assert candidate.technical_context["diagnosis_quality"]["score"] >= 80
    assert candidate.technical_context["patch_candidate_quality"]["score"] >= 80
    assert candidate.technical_context["actionability"]["editable"] is True
    assert candidate.technical_context["alignment"]["aligned"] is True
    assert candidate.technical_context["repair_intent"]["expected_behavior"] == "render returns the fresh value."
    assert candidate.technical_context["semantic_evidence"]["coverage_score"] > 0
    assert candidate.technical_context["behavior_localization"]["coverage_score"] > 0
    assert candidate.technical_context["behavior_justification"]["coverage_score"] > 0
    assert candidate.technical_context["candidate_transformation"]["coverage_score"] > 0
    assert candidate.technical_context["repair_task"]["candidate_id"] == candidate.candidate_id
