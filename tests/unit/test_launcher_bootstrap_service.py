from aipinho.schemas.supervisor.contracts import ServiceHealth
from aipinho.services.supervisor.launcher_bootstrap_service import LauncherBootstrapService
from aipinho.services.supervisor.launcher_watchdog_service import LauncherWatchdogService


def test_launcher_bootstrap_monitor_first_and_token():
    result = LauncherBootstrapService().bootstrap()
    assert result["monitor_first"] is True
    assert result["planned_start_order"][0] == "monitor_supervisor"
    assert result["token_configured"] is True


def test_launcher_watchdog_controls_monitor():
    watchdog = LauncherWatchdogService()
    assert watchdog.status()["launcher_controls_monitor"] is True
    assert watchdog.should_restart_monitor(ServiceHealth(service_id="monitor_supervisor", status="down")) is True
    assert watchdog.should_restart_monitor(ServiceHealth(service_id="monitor_supervisor", status="healthy")) is False
