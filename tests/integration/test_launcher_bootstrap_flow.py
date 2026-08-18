from aipinho.services.supervisor.launcher_bootstrap_service import LauncherBootstrapService
from aipinho.services.supervisor.launcher_watchdog_service import LauncherWatchdogService
from aipinho.schemas.supervisor.contracts import ServiceHealth


def test_launcher_bootstrap_flow_monitor_first_and_watchdog():
    boot = LauncherBootstrapService().bootstrap()
    assert boot["planned_start_order"][0] == "monitor_supervisor"
    assert LauncherWatchdogService().should_restart_monitor(ServiceHealth(service_id="monitor_supervisor", status="down")) is True
