from aipinho.services.validation.validation_gate_service import ValidationGateService
from aipinho.services.validation.validation_store import ValidationStore
from validation_fixtures import report_missing_evidence, valid_report, valid_task_result


def _gate(tmp_path):
    return ValidationGateService(store=ValidationStore(root=tmp_path / "validations"))


def test_validation_gate_passes_valid_report(tmp_path):
    result = _gate(tmp_path).validate_report_payload(valid_report())
    assert result.status in {"passed", "passed_with_warnings"}


def test_validation_gate_rejects_finding_without_evidence(tmp_path):
    result = _gate(tmp_path).validate_report_payload(report_missing_evidence())
    assert result.status == "rejected"
    assert "missing_evidence" in result.blocking_findings


def test_validation_gate_flags_side_effect_payload(tmp_path):
    result = _gate(tmp_path).validate_side_effects({"events": [{"action": "write_files", "status": "completed"}]})
    assert result.status == "failed"
    assert "side_effect_violation" in result.blocking_findings


def test_validation_gate_validates_task_result_payload(tmp_path):
    result = _gate(tmp_path).validate_task_result_payload(valid_task_result())
    assert result.status in {"passed", "passed_with_warnings"}
