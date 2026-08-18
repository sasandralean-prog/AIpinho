from __future__ import annotations

from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.services.patching.patch_candidate_actionability_analyzer import PatchCandidateActionabilityAnalyzer


def test_actionability_accepts_bounded_concrete_repair_task():
    candidate = PatchCandidateArtifact(
        diagnosis_id="diagnosis_1",
        workspace="workspace",
        semantic_goal="Return fresh value from render.",
        target_file="src/app.py",
        target_symbol="render",
        symbol_kind="function",
        observed_behavior="render returns the stale value.",
        expected_behavior="render returns the fresh value.",
        evidence_refs=["artifact_1"],
        confidence=0.8,
        replacement_strategy="Update the stale return branch.",
        current_content_excerpt="def render():\n    return 'old'\n",
    )

    result = PatchCandidateActionabilityAnalyzer().analyze(candidate)

    assert result.editable is True
    assert result.score >= 75
    assert result.repair_task.actionable is True


def test_actionability_blocks_generic_file_task_without_complete_context():
    candidate = PatchCandidateArtifact(
        diagnosis_id="diagnosis_1",
        workspace="workspace",
        semantic_goal="Produce patch preview.",
        target_file="src/app.py",
        target_symbol="src/app.py",
        symbol_kind="file",
        observed_behavior="File context selected.",
        expected_behavior="Produce a concrete replacement candidate.",
        evidence_refs=["artifact_1"],
        confidence=0.5,
        replacement_strategy="Return replacement text.",
        current_content_excerpt="print('old')\n",
        technical_context={"current_content_complete": False, "current_content_chars": 13, "source_content_chars": 100},
    )

    result = PatchCandidateActionabilityAnalyzer().analyze(candidate)

    assert result.editable is False
    assert "REPAIR_TASK_NOT_ACTIONABLE" in result.reason_codes
    assert "REPAIR_TASK_SNIPPET_INSUFFICIENT" in result.reason_codes


def test_actionability_blocks_operational_text_as_expected_behavior():
    candidate = PatchCandidateArtifact(
        diagnosis_id="diagnosis_1",
        workspace="workspace",
        semantic_goal="Generate patch planning artifacts.",
        target_file="src/app.py",
        target_symbol="render",
        symbol_kind="function",
        observed_behavior="render returns the stale value.",
        expected_behavior="Generate patch preview, rollback, validation report, and artifacts.",
        evidence_refs=["artifact_1"],
        confidence=0.8,
        replacement_strategy="Update render.",
        current_content_excerpt="def render():\n    return 'old'\n",
    )

    result = PatchCandidateActionabilityAnalyzer().analyze(candidate)

    assert result.editable is False
    assert "REPAIR_TASK_EXPECTED_BEHAVIOR_OPERATIONAL" in result.reason_codes
