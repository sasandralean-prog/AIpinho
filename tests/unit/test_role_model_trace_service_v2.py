from aipinho.services.roles.role_model_trace_service import RoleModelTraceService


def test_role_model_trace_records_sanitized_role_event():
    service = RoleModelTraceService()

    trace_id = service.create("coder", summary="test trace")
    service.record(trace_id, role_id="coder", event_type="role_model_gate_v2", status="ok", summary="gate ok")
    trace = service.get(trace_id)

    assert trace["trace_id"] == trace_id
    assert trace["category"] == "role_model"
    assert any(event["event_type"] == "role_model_gate_v2" for event in trace["events"])
