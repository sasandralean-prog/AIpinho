from pathlib import Path

from aipinho.schemas.models.manual_inference_result import ManualInferenceResult
from aipinho.services.models.smoke_test_audit_service import SmokeTestAuditService


def test_smoke_test_audit_service_records_sanitized_audit_event(tmp_path):
    audit_path = tmp_path / "audit" / "manual_inference_smoke.jsonl"
    service = SmokeTestAuditService(config={"store": {"audit_log": str(audit_path)}})
    result = ManualInferenceResult(status="blocked", violations=["manual_inference_disabled"], warnings=["safe_warning"])
    event = service.record(result)
    assert event.run_id == result.run_id
    assert event.status == "blocked"
    assert audit_path.exists()
    text = audit_path.read_text(encoding="utf-8")
    assert "manual_inference_disabled" in text
    assert "output_preview" not in text
    assert "prompt" not in text.lower()
