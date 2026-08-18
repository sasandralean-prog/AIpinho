from aipinho.services.models.model_trace_service import ModelTraceService


def test_model_trace_service_records_sanitized_event(tmp_path):
    service = ModelTraceService()
    service.trace_service.store_dir = tmp_path
    trace_id = service.create_model_trace(model_id="x")
    service.record(trace_id, event_type="doctor", status="ok", summary="done", model_id="x", data={"api_key": "secret"})
    trace = service.get_trace(trace_id)
    assert trace["trace_id"] == trace_id
    assert trace["events"][-1]["data"]["api_key"] == "[REDACTED]"
