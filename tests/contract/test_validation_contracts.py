from aipinho.schemas.validation import EvidenceCompliance, ReportQualityResult, SideEffectValidation, ValidationFinding, ValidationGateResult, ValidationRequest


def test_validation_request_contract():
    request = ValidationRequest(target_type="project_report", payload={"x": 1})
    assert request.target_type == "project_report"


def test_validation_gate_result_contract():
    finding = ValidationFinding(finding_id="vf1", code="missing_evidence", title="Missing", message="missing", severity="critical", validator="test", blocking=True)
    result = ValidationGateResult(validation_id="validation_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", target_type="project_report", status="rejected", score=0.0, findings=[finding], blocking_findings=["missing_evidence"])
    assert result.summary()["status"] == "rejected"


def test_report_quality_side_effect_and_evidence_contracts():
    report = ReportQualityResult(validation_id="validation_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", status="passed", score=1.0)
    side = SideEffectValidation(status="passed", side_effects_detected=False)
    evidence = EvidenceCompliance(status="passed", findings_checked=1, evidence_checked=1)
    assert report.status == side.status == evidence.status == "passed"
