import pytest
from pydantic import ValidationError
from aipinho.schemas.regression.contracts import RegressionCaseCandidate, RegressionStatus

def test_regression_contract_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        RegressionStatus(extra=True)

def test_candidate_starts_unpromoted():
    candidate = RegressionCaseCandidate(source_type="feedback", category="policy", severity="high", evidence=[{"id":"e"}], expected_behavior={"write_allowed":False})
    assert candidate.promoted is False
