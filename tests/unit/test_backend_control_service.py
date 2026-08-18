from __future__ import annotations

from aipinho.schemas.supervisor.contracts import ServiceHealth
from aipinho.services.supervisor.backend_control_service import BackendControlService


class _Completed:
    returncode = 0
    stdout = "done\n"
    stderr = ""


class _Health:
    def check(self, service, timeout_seconds=1.0):
        return ServiceHealth(service_id=service.service_id, status="healthy", http_status=200, human_message="ok")


def _runner(argv, **kwargs):
    assert kwargs["shell"] is False
    assert "powershell.exe" in argv[0]
    assert "-File" in argv
    return _Completed()


def test_backend_control_status_uses_9099_control_plane():
    service = BackendControlService(health=_Health(), runner=_runner)

    status = service.status()

    assert status.status == "online"
    assert status.backend_port == 9088
    assert status.control_port == 9099
    assert status.exclusive_control_port is True


def test_backend_control_restart_runs_canonical_scripts_with_fake_runner():
    service = BackendControlService(health=_Health(), runner=_runner)

    result = service.restart(served_port=9099, requested_by="test")

    assert result.allowed is True
    assert result.status == "accepted"
    assert result.backend_port == 9088
    assert result.control_port == 9099
    assert result.audit_id
    assert result.trace_id


def test_backend_control_blocks_wrong_served_port():
    service = BackendControlService(health=_Health(), runner=_runner)

    result = service.restart(served_port=9088, requested_by="test")

    assert result.allowed is False
    assert result.status == "blocked"
    assert "backend_control_port_required" in result.blocked_reasons
