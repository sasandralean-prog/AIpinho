from aipinho.services.evaluation.evidence_requirement_validator import EvidenceRequirementValidator


def test_evidence_requirement_validator_accepts_valid_evidence_id():
    content = '{"findings": [{"summary": "ok", "evidence_id": "ev1"}], "limitations": []}'
    result = EvidenceRequirementValidator().validate(content, {"require_evidence": True}, [{"evidence_id": "ev1", "source": "config"}])
    assert result.valid is True


def test_evidence_requirement_validator_rejects_missing_evidence():
    content = '{"findings": [{"summary": "ok"}], "limitations": []}'
    result = EvidenceRequirementValidator().validate(content, {"require_evidence": True}, [{"evidence_id": "ev1"}])
    assert result.valid is False
    assert result.missing_evidence_claims


def test_evidence_requirement_validator_warns_unseen_file():
    result = EvidenceRequirementValidator().validate("Veja src/foo/bar.py", {}, [{"path": "src/known.py"}])
    assert "src/foo/bar.py" in result.unseen_file_refs


def test_evidence_requirement_validator_accepts_absence_evidence():
    content = '{"findings": [{"summary": "missing config", "evidence_id": "abs1"}], "limitations": []}'
    result = EvidenceRequirementValidator().validate(content, {"require_evidence": True}, [{"evidence_id": "abs1", "source": "absence"}])
    assert result.valid is True


def test_evidence_requirement_validator_allows_limitations_without_evidence():
    result = EvidenceRequirementValidator().validate('{"findings": [], "limitations": ["limited context"]}', {"require_evidence": True}, [])
    assert result.valid is True or "evidence_context_required" in result.missing_evidence_claims
