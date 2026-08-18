from aipinho.schemas.maintenance.contracts import DiagnosisRequest
from aipinho.services.maintenance.diagnosis_service import DiagnosisService

def test_diagnosis_without_evidence_is_rejected():
    result = DiagnosisService().diagnose(DiagnosisRequest())
    assert result.status == "rejected"
    assert "diagnosis_evidence_required" in result.reasons
