from aipinho.services.regression.regression_candidate_service import RegressionCandidateService

def test_candidate_is_not_promoted_automatically():
    candidate = RegressionCandidateService().create("feedback", "policy", "high", [{"source":"test"}], {"write_allowed":False})
    assert candidate.promoted is False
    assert candidate.status == "candidate"
