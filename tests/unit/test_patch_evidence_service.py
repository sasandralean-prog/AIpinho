from aipinho.services.patching.patch_evidence_service import PatchEvidenceService


def test_patch_evidence_service_requires_evidence():
    service = PatchEvidenceService()
    ok, reasons = service.validate([])
    assert ok is False
    assert "missing_evidence" in reasons
    generated = service.normalize([], user_request="fix", affected_paths=["src/app.py"])
    assert generated
    assert service.validate(generated)[0] is True
