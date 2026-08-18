from aipinho.services.validation.validation_common import finding
from aipinho.services.validation.validation_score_service import ValidationScoreService


def test_validation_score_passed_score():
    score = ValidationScoreService().score([])
    assert score.status == "passed"


def test_validation_score_needs_review_score():
    findings = [finding("unsupported_claim", "Claim", "unsupported", severity="warning", validator="test") for _ in range(3)]
    score = ValidationScoreService().score(findings)
    assert score.status in {"passed_with_warnings", "needs_review"}


def test_validation_score_critical_override():
    score = ValidationScoreService().score([finding("side_effect_violation", "Write", "write", severity="critical", validator="test")])
    assert score.status == "failed"


def test_validation_score_rejected_override_for_secret():
    score = ValidationScoreService().score([finding("secret_leak", "Secret", "secret", severity="critical", validator="test")])
    assert score.status == "rejected"
