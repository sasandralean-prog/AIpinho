from aipinho.schemas.supervisor.contracts import ServiceDefinition
from aipinho.services.supervisor.service_health_checker import ServiceHealthChecker


def service(url: str) -> ServiceDefinition:
    return ServiceDefinition(service_id="svc", display_name="Svc", port=1, health_url=url, command_profile="profile")


def test_health_checker_healthy_down_timeout_and_degraded():
    checker = ServiceHealthChecker()
    assert checker.check(service("mock://healthy")).status == "healthy"
    assert checker.check(service("mock://down")).status == "down"
    assert checker.check(service("mock://timeout")).error == "timeout"
    degraded = checker.check(service("mock://degraded"))
    assert degraded.status == "degraded"
    assert degraded.latency_ms == 1500
