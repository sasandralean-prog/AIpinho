from aipinho.schemas.maintenance.contracts import DiagnosisEvidence, DiagnosisRequest
from aipinho.services.maintenance.diagnosis_evidence_collector import DiagnosisEvidenceCollector

def test_builds_ephemeral_context_bundle_with_trace():
    request = DiagnosisRequest(evidence=[DiagnosisEvidence(source_type="event_summary", source_id="event_unit", summary="Observed state.", event_ref="event_unit")])
    evidence, bundle_id, trace_id = DiagnosisEvidenceCollector().collect(request)
    assert evidence and bundle_id.startswith("bundle_")
    assert trace_id.startswith("context_trace_")
