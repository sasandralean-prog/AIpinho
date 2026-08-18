from __future__ import annotations

from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.services.patching.diagnosis_alignment_validator import DiagnosisAlignmentValidator


def test_alignment_accepts_targeted_editable_snippet():
    candidate = PatchCandidateArtifact(
        diagnosis_id="diagnosis_1",
        workspace="workspace",
        semantic_goal="decode validates short input before indexed access.",
        target_file="src/decoder.py",
        target_symbol="decode",
        symbol_kind="function",
        observed_behavior="decode reads past the available bytes on short input.",
        expected_behavior="decode must validate short input before indexed access.",
        evidence_refs=["artifact_1"],
        confidence=0.8,
        replacement_strategy="Update decode bounds validation.",
        current_content_excerpt="def decode(data):\n    if len(data) < 5:\n        return error('short input')\n    return data[4]\n",
        technical_context={
            "repair_intent": {
                "success_condition": "decode no longer performs indexed access without validating input bounds.",
                "repair_boundary": ["Preserve the decode signature."],
            },
            "repair_task": {
                "success_condition": "decode no longer performs indexed access without validating input bounds.",
                "repair_boundary": ["Preserve the decode signature."],
            },
            "semantic_evidence": {
                "coverage_score": 100,
                "status": "complete",
            },
            "behavior_localization": {
                "coverage_score": 100,
                "status": "complete",
            },
            "behavior_justification": {
                "coverage_score": 100,
                "status": "complete",
            },
            "candidate_transformation": {
                "coverage_score": 100,
                "status": "complete",
            },
        },
    )

    result = DiagnosisAlignmentValidator().analyze(candidate)

    assert result.aligned is True
    assert result.score >= 70
    assert "semantic_alignment" in result.present


def test_alignment_blocks_semantically_misaligned_snippet():
    candidate = PatchCandidateArtifact(
        diagnosis_id="diagnosis_1",
        workspace="workspace",
        semantic_goal="decoder must handle truncated input safely.",
        target_file="src/AdaptivePcmDecoder.kt",
        target_symbol="selectDecoder",
        symbol_kind="function",
        observed_behavior="The decoder reads past available bytes when the input stream is truncated.",
        expected_behavior="selectDecoder must detect incomplete input before reading past available data.",
        evidence_refs=["artifact_1"],
        confidence=0.8,
        replacement_strategy="Update decoder handling.",
        current_content_excerpt=(
            "fun selectDecoder(extension: String): Decoder {\n"
            "    return when (extension.lowercase()) {\n"
            "        \"wav\" -> wavDecoder\n"
            "        else -> pcmDecoder\n"
            "    }\n"
            "}\n"
        ),
        technical_context={
            "repair_intent": {
                "success_condition": "selectDecoder handles incomplete input without invalid reads.",
                "repair_boundary": ["Preserve decoder selection contracts."],
            },
            "repair_task": {
                "success_condition": "selectDecoder handles incomplete input without invalid reads.",
                "repair_boundary": ["Preserve decoder selection contracts."],
            },
            "semantic_evidence": {
                "coverage_score": 100,
                "status": "complete",
            },
            "behavior_localization": {
                "coverage_score": 30,
                "status": "partial",
            },
            "behavior_justification": {
                "coverage_score": 70,
                "status": "partial",
            },
            "candidate_transformation": {
                "coverage_score": 30,
                "status": "partial",
            },
        },
    )

    result = DiagnosisAlignmentValidator().analyze(candidate)

    assert result.aligned is False
    assert "REPAIR_TASK_ALIGNMENT_FAILED" in result.reason_codes
    assert "DIAGNOSIS_ALIGNMENT_MISSING" in result.reason_codes
    assert "semantic alignment" in result.gaps
