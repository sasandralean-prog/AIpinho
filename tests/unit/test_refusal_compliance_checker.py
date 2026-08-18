from aipinho.services.evaluation.refusal_compliance_checker import RefusalComplianceChecker


def test_refusal_compliance_checker_accepts_clear_refusal_when_blocked():
    result = RefusalComplianceChecker().check("Bloqueado por policy.", {"status": "blocked"}, {})
    assert result["valid"] is True
    assert result["required"] is True


def test_refusal_compliance_checker_rejects_execution_claim_in_blocked_response():
    result = RefusalComplianceChecker().check("Executei o comando.", {"status": "blocked"}, {})
    assert result["valid"] is False
    assert "blocked_response_claims_execution" in result["violations"]


def test_refusal_compliance_checker_warns_when_refusal_is_unclear():
    result = RefusalComplianceChecker().check("Isso nao sera feito agora.", {"status": "blocked"}, {})
    assert "missing_clear_refusal_explanation" in result["warnings"]
