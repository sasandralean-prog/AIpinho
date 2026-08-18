from __future__ import annotations

from aipinho.schemas.patching.canonical_diagnosis_artifact import (
    CanonicalDiagnosisArtifact,
    DiagnosisEvidenceRef,
    RepairHint,
    RepairIntent,
    TechnicalLocalization,
)
from aipinho.services.patching.patch_candidate_builder import PatchCandidateBuilder


def test_builder_promotes_repair_intent_expected_behavior_over_operational_objective():
    diagnosis = CanonicalDiagnosisArtifact(
        workspace="workspace",
        semantic_goal="Generate patch planning artifacts and rollback report.",
        observed_behavior="decode raises IndexOutOfBoundsException on short input.",
        expected_behavior="Generate patch preview, risk report, rollback, and validation artifacts.",
        technical_localization=[
            TechnicalLocalization(
                workspace="workspace",
                target_file="src/decoder.py",
                target_symbol="decode",
                symbol_kind="function",
                confidence=0.8,
            )
        ],
        evidence=[DiagnosisEvidenceRef(evidence_id="evidence_1", summary="decode fails on short input.", confidence=0.8)],
        confidence=0.8,
        repair_hints=[RepairHint(strategy="Generate patch preview, risk report, rollback, and validation artifacts.")],
        repair_intent=RepairIntent(
            target_file="src/decoder.py",
            target_symbol="decode",
            expected_behavior="decode must validate short input before indexed access.",
            success_condition="decode no longer performs indexed access before validating input bounds.",
            repair_boundary=["Preserve the decode signature."],
            evidence_refs=["evidence_1"],
            confidence=0.8,
        ),
    )

    candidate = PatchCandidateBuilder().from_diagnosis(
        diagnosis,
        current_content_by_path={"src/decoder.py": "def decode(data):\n    return data[4]\n"},
    )[0]

    assert candidate.expected_behavior == "decode must validate short input before indexed access."
    assert candidate.semantic_goal == "decode no longer performs indexed access before validating input bounds."
    assert candidate.replacement_strategy == (
        "Edit decode to validate bounds before indexed or offset-based reads and route insufficient input through the existing failure contract."
    )
    assert "Preserve the decode signature." in candidate.optional_constraints
    assert candidate.technical_context["repair_intent"]["expected_behavior"] == candidate.expected_behavior


def test_builder_prefers_symbol_excerpt_over_file_prefix():
    diagnosis = CanonicalDiagnosisArtifact(
        workspace="workspace",
        semantic_goal="Repair decode behavior.",
        observed_behavior="decode raises IndexOutOfBoundsException on short input.",
        expected_behavior="decode must validate short input before indexed access.",
        technical_localization=[
            TechnicalLocalization(
                workspace="workspace",
                target_file="src/decoder.py",
                target_symbol="decode",
                symbol_kind="function",
                confidence=0.8,
            )
        ],
        evidence=[DiagnosisEvidenceRef(evidence_id="evidence_1", summary="decode fails on short input.", confidence=0.8)],
        confidence=0.8,
        repair_hints=[RepairHint(strategy="Update decode bounds validation.")],
    )

    candidate = PatchCandidateBuilder().from_diagnosis(
        diagnosis,
        current_content_by_path={
            "src/decoder.py": (
                "def helper():\n"
                "    return 'helper'\n\n"
                "def decode(data):\n"
                "    return data[4]\n"
            )
        },
    )[0]

    assert candidate.current_content_excerpt is not None
    assert candidate.current_content_excerpt.startswith("def decode")
    assert "def helper" not in candidate.current_content_excerpt
    assert candidate.technical_context["localized_excerpt"] is True
