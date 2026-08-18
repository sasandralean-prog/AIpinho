from aipinho.schemas.supervisor.contracts import ServiceDefinition, ServiceStatus, PortStatus, SupervisorStatus, ServiceRestartRequest, ServiceRestartResult, ConnectionProfile, MobilePairingResult


def test_supervisor_contracts_construct():
    svc = ServiceDefinition(service_id="core_backend", display_name="Core", port=9088, health_url="mock://healthy", command_profile="profile")
    status = ServiceStatus(service_id="core_backend", display_name="Core", port=9088, health_url="mock://healthy", status="healthy", restartable=True, monitor_can_restart=True)
    port = PortStatus(port=9088, service_id="core_backend", status="closed")
    sup = SupervisorStatus(status="partial", services=[status], ports=[port])
    req = ServiceRestartRequest(service_id="core_backend")
    result = ServiceRestartResult(service_id="core_backend", port=9088, status="accepted", allowed=True)
    profile = ConnectionProfile(profile_id="manual", display_name="Manual")
    pairing = MobilePairingResult(status="created", token_configured=True, token="secret")
    assert svc.port == 9088 and sup.monitor_port == 9099 and req.service_id and result.allowed and profile.profile_id and pairing.token
