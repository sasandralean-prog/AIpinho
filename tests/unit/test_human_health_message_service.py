from aipinho.schemas.supervisor.contracts import ServiceStatus
from aipinho.services.supervisor.human_health_message_service import HumanHealthMessageService


def status(service_id, port, state, can=True, latency=None):
    return ServiceStatus(service_id=service_id, display_name=service_id, port=port, health_url="mock://"+state, status=state, restartable=can, monitor_can_restart=can, latency_ms=latency, human_message=f"{service_id} {state}")


def test_human_health_messages_cover_healthy_down_degraded_and_monitor_blocked():
    svc = HumanHealthMessageService()
    assert svc.messages([status("core_backend", 9088, "healthy")])[0].severity == "healthy"
    assert svc.messages([status("core_backend", 9088, "down")])[0].severity == "down"
    assert svc.messages([status("artifact_service", 9098, "degraded", latency=1500)])[0].severity == "degraded"
    messages = svc.messages([status("monitor_supervisor", 9099, "healthy", can=False)])
    assert any(m.severity == "blocked" for m in messages)
