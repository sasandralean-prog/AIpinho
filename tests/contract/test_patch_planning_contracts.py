from aipinho.schemas.patching import AffectedFile, DiffProposal, PatchEvidence, PatchHunk, PatchPlan, PatchPlanRequest, PatchRiskAssessment, RollbackNote, TestRecommendation


def test_patch_planning_contracts_validate():
    PatchPlanRequest(workspace="w")
    AffectedFile(path="docs/a.md")
    PatchEvidence(evidence_id="e", excerpt="x")
    PatchHunk(hunk_id="h", file_path="docs/a.md", original="a", replacement="b")
    DiffProposal(proposal_id="d", plan_id="p")
    PatchRiskAssessment()
    RollbackNote(file_path="docs/a.md")
    TestRecommendation(test_type="review", command="manual review")
    PatchPlan(plan_id="patch_plan_abcdef", status="blocked", workspace="w", created_at="now", updated_at="now")
