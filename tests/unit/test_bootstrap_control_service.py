from __future__ import annotations

from aipinho.schemas.supervisor.contracts import ServiceDefinition, ServiceHealth
from aipinho.services.supervisor.bootstrap_control_service import BootstrapControlService


class _Registry:
    def get(self, service_id: str):
        if service_id != "monitor_supervisor":
            return None
        return ServiceDefinition(
            service_id="monitor_supervisor",
            display_name="Monitor",
            port=9099,
            health_url="mock://healthy",
            command_profile="aipinho_monitor_9099",
        )


class _Health:
    def check(self, service, timeout_seconds: float = 1.0):
        return ServiceHealth(service_id=service.service_id, status="healthy", http_status=200)


class _Recorder:
    def record(self, item):
        return item


def test_bootstrap_control_restarts_only_monitor_with_canonical_scripts() -> None:
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return Result()

    service = BootstrapControlService(
        registry=_Registry(),
        health=_Health(),
        audit=_Recorder(),
        traces=_Recorder(),
        events=_Recorder(),
        runner=runner,
    )

    result = service.restart_monitor()

    assert result.allowed is True
    assert result.controlled_port == 9099
    assert len(calls) == 2
    assert all("-File" in command for command, _ in calls)
    assert all("9099" in command for command, _ in calls)
    assert all(kwargs.get("shell") is False for _, kwargs in calls)


def test_bootstrap_control_blocks_when_custom_command_policy_is_disabled() -> None:
    service = BootstrapControlService(
        registry=_Registry(),
        health=_Health(),
        audit=_Recorder(),
        traces=_Recorder(),
        events=_Recorder(),
        runner=lambda *args, **kwargs: None,
    )
    service.policy = {
        "bootstrap_control": {
            "enabled": True,
            "no_custom_command_from_request": False,
        }
    }

    result = service.restart_monitor()

    assert result.allowed is False
    assert "bootstrap_policy_requires_no_custom_command" in result.blocked_reasons
