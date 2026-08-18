from aipinho.services.regression.regression_candidate_service import RegressionCandidateService
from aipinho.schemas.regression.contracts import RegressionPromotionRequest
from aipinho.services.regression.regression_promotion_service import RegressionPromotionService

def test_promotion_requires_approval_and_validation():
    candidate = RegressionCandidateService().create("feedback", "policy", "high", [{"source":"test"}], {"write_allowed":False})
    blocked = RegressionPromotionService().promote(RegressionPromotionRequest(candidate_id=candidate.candidate_id))
    assert blocked.status == "blocked"
    promoted = RegressionPromotionService().promote(RegressionPromotionRequest(candidate_id=candidate.candidate_id, approved=True, validation_passed=True))
    assert promoted.status == "promoted"
