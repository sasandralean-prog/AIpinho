from aipinho.schemas.supervisor.contracts import ServiceRestartRequest
from aipinho.services.supervisor.service_restart_service import ServiceRestartService


def test_restart_allowed_ports_and_blocks_monitor_unknown_and_command():
    service = ServiceRestartService()
    for sid, port in [("core_backend", 9088), ("interaction_gateway", 9089), ("artifact_service", 9098)]:
        result = service.restart_service(ServiceRestartRequest(service_id=sid, port=port))
        assert result.allowed is True
        assert result.status == "accepted"
        assert result.trace_id
        assert result.audit_id
    blocked = service.restart_service(ServiceRestartRequest(service_id="monitor_supervisor", port=9099))
    assert blocked.allowed is False
    assert "monitor_cannot_restart_itself" in blocked.blocked_reasons
    assert service.restart_service(ServiceRestartRequest(service_id="missing")).blocked_reasons == ["unknown_service"]
    assert service.restart_service(ServiceRestartRequest(service_id="core_backend", command="whoami")).blocked_reasons == ["arbitrary_command_blocked"]
    assert service.restart_port(ServiceRestartRequest(port=12345)).blocked_reasons == ["unknown_port"]
