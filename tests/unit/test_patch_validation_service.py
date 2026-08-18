from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.diff_preview import DiffPreview
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_risk import PatchRiskAssessment
from aipinho.schemas.patching.rollback_note import RollbackNote
from aipinho.schemas.patching.test_recommendation import TestRecommendation
from aipinho.services.patching.patch_validation_service import PatchValidationService


def test_patch_validation_rejects_missing_evidence_and_accepts_preview():
    service = PatchValidationService()
    invalid = service.validate(evidence=[], diff=None, risk=PatchRiskAssessment(risk_level="critical", blocked=True), rollback_notes=[], test_recommendations=[])
    assert invalid.status == "blocked"
    valid = service.validate(
        evidence=[PatchEvidence(evidence_id="e1", excerpt="x")],
        diff=DiffProposal(proposal_id="d", plan_id="p", status="generated", diff=DiffPreview(diff_text="--- a\n+++ b\n-x\n+y", chars=20)),
        risk=PatchRiskAssessment(risk_level="low", needs_review=False),
        rollback_notes=[RollbackNote(file_path="docs/a.md", summary="manual")],
        test_recommendations=[TestRecommendation(test_type="review", command="manual review")],
    )
    assert valid.valid is True
