from __future__ import annotations

from aipinho.schemas.patching.canonical_diagnosis_artifact import (
    CanonicalDiagnosisArtifact,
    DiagnosisEvidenceRef,
    TechnicalLocalization,
)
from aipinho.services.patching.repair_intent_resolver import RepairIntentResolver


def _diagnosis(
    *,
    observed_behavior: str,
    expected_behavior: str = "Produce patch preview.",
    target_file: str = "src/decoder.py",
    target_symbol: str = "decode",
) -> CanonicalDiagnosisArtifact:
    return CanonicalDiagnosisArtifact(
        workspace="workspace",
        semantic_goal="Repair bounded technical behavior.",
        observed_behavior=observed_behavior,
        expected_behavior=expected_behavior,
        technical_localization=[
            TechnicalLocalization(
                workspace="workspace",
                target_file=target_file,
                target_symbol=target_symbol,
                symbol_kind="function",
                confidence=0.8,
            )
        ],
        evidence=[DiagnosisEvidenceRef(evidence_id="artifact_1", summary=observed_behavior, confidence=0.8)],
        confidence=0.8,
    )


def test_repair_intent_preserves_existing_target_specific_behavior():
    diagnosis = _diagnosis(
        observed_behavior="decode raises IndexOutOfBoundsException on short input.",
        expected_behavior="decode must validate short input before indexed access.",
    )

    enriched = RepairIntentResolver().enrich(diagnosis)

    assert enriched.repair_intent is not None
    assert enriched.expected_behavior == "decode must validate short input before indexed access."
    assert enriched.repair_intent.success_condition == enriched.expected_behavior
    assert "REPAIR_INTENT_RESOLVED_FROM_DIAGNOSIS" in enriched.reason_codes


def test_repair_intent_synthesizes_from_diagnosis_type_without_llm():
    diagnosis = _diagnosis(
        observed_behavior="decode raises IndexOutOfBoundsException when the input buffer is shorter than the header.",
    )

    first = RepairIntentResolver().enrich(diagnosis)
    second = RepairIntentResolver().enrich(diagnosis)

    assert first.repair_intent is not None
    assert first.repair_intent.expected_behavior == second.repair_intent.expected_behavior
    assert "decode" in first.expected_behavior
    assert "boundary" in first.repair_intent.success_condition
    assert "REPAIR_INTENT_BOUNDS_RESOLVED" in first.reason_codes


def test_repair_intent_does_not_invent_for_generic_planning_text():
    diagnosis = _diagnosis(
        observed_behavior="Patch planning artifacts were requested.",
        expected_behavior="Produce a concrete patch preview with risk and rollback.",
    )

    enriched = RepairIntentResolver().enrich(diagnosis)

    assert enriched.repair_intent is None
    assert enriched.expected_behavior == diagnosis.expected_behavior
    assert "REPAIR_INTENT_MISSING" in enriched.reason_codes
    assert "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING" in enriched.reason_codes


def test_repair_intent_rejects_operational_target_specific_expected_behavior():
    diagnosis = _diagnosis(
        observed_behavior="decode raises IndexOutOfBoundsException on short input.",
        expected_behavior=(
            "decode in src/decoder.py must generate reports/patch_preview.md, rollback instructions, "
            "validation output, and completion evidence."
        ),
    )

    enriched = RepairIntentResolver().enrich(diagnosis)

    assert enriched.repair_intent is not None
    assert "reports/" not in enriched.repair_intent.expected_behavior
    assert "patch_preview" not in enriched.repair_intent.expected_behavior.casefold()
    assert "boundar" in enriched.repair_intent.expected_behavior.casefold()
    assert "REPAIR_INTENT_BOUNDS_RESOLVED" in enriched.reason_codes
