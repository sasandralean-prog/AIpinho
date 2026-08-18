from patch_fixtures import patch_request, patch_workspace
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest
from aipinho.services.patching.patch_planning_service import PatchPlanningService


def test_patch_planning_service_valid_plan_no_write(tmp_path):
    workspace = patch_workspace(tmp_path)
    before = (workspace / "docs" / "note.md").read_text(encoding="utf-8")
    result = PatchPlanningService().create_plan(patch_request(workspace))
    assert result.plan.status in {"ready_for_review", "needs_review"}
    assert result.plan.apply_enabled is False
    assert result.plan.write_enabled is False
    assert result.plan.diff_proposal is not None
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8") == before


def test_patch_planning_service_blocks_missing_evidence_and_forbidden_root(tmp_path):
    workspace = patch_workspace(tmp_path)
    missing = PatchPlanningService().create_plan(PatchPlanRequest(workspace=str(workspace), affected_files=["docs/note.md"]))
    assert missing.plan.status == "blocked"
    forbidden = PatchPlanningService().create_plan(PatchPlanRequest(workspace=r"C:\Windows", affected_files=["docs/note.md"], objective="x"))
    assert forbidden.plan.status == "blocked"


def test_patch_planning_service_does_not_invent_replacement(tmp_path):
    workspace = patch_workspace(tmp_path)
    request = patch_request(workspace).model_copy(update={"replacements": {}})

    result = PatchPlanningService().create_plan(request)

    assert result.plan.status == "blocked"
    assert result.plan.diff_proposal is None
    assert "INSUFFICIENT_PATCH_EVIDENCE" in result.plan.blocked_reasons
    assert "missing_diff" in result.plan.validation.blocked_reasons


def test_patch_planning_service_compiles_candidate_artifact_to_diff(tmp_path):
    workspace = patch_workspace(tmp_path)
    candidate = PatchCandidateArtifact(
        workspace=str(workspace),
        task_run_id="task_run_test",
        execution_plan_id="execution_test",
        semantic_goal="Replace old output.",
        target_file="src/app.py",
        target_symbol="src/app.py",
        symbol_kind="file",
        observed_behavior="The current file prints old.",
        expected_behavior="The file should print new.",
        evidence_refs=["e1"],
        confidence=0.8,
    )
    request = patch_request(workspace, path="src/app.py").model_copy(
        update={"patch_candidates": [candidate], "replacements": {"src/app.py": "print('new')\n"}}
    )

    result = PatchPlanningService().create_plan(request)

    assert result.plan.status in {"ready_for_review", "needs_review"}
    assert result.plan.diagnosis_artifacts
    assert result.plan.patch_candidates
    assert result.plan.patch_candidates[0].diagnosis_id
    assert result.plan.hunks
    assert result.plan.diff_proposal is not None


def test_patch_planning_service_derives_candidate_from_canonical_diagnosis(tmp_path):
    workspace = patch_workspace(tmp_path)
    request = patch_request(workspace, path="src/app.py")

    result = PatchPlanningService().create_plan(request)

    assert result.plan.diagnosis_artifacts
    assert result.plan.patch_candidates
    assert result.plan.patch_candidates[0].diagnosis_id == result.plan.diagnosis_artifacts[0].diagnosis_id


def test_patch_planning_service_blocks_candidate_without_symbol_context(tmp_path):
    workspace = patch_workspace(tmp_path)
    candidate = PatchCandidateArtifact(
        workspace=str(workspace),
        semantic_goal="Change a missing function.",
        target_file="src/app.py",
        target_symbol="missing_function",
        symbol_kind="function",
        observed_behavior="Missing symbol is referenced by evidence.",
        expected_behavior="Symbol should be changed.",
        evidence_refs=["e1"],
        confidence=0.8,
    )
    request = patch_request(workspace, path="src/app.py").model_copy(
        update={"patch_candidates": [candidate], "replacements": {"src/app.py": "def missing_function():\n    return True\n"}}
    )

    result = PatchPlanningService().create_plan(request)

    assert result.plan.status == "blocked"
    assert "PATCH_SYMBOL_NOT_FOUND" in result.plan.blocked_reasons
    assert result.plan.diff_proposal is None
