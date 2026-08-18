from aipinho.services.mobile.mobile_status_service import MobileStatusService
def test_mobile_restart_allowlist():
    s=MobileStatusService().status(); assert s["mobile_restart_allowed_ports"]==[9088,9089,9098]; assert s["mobile_restart_blocked_ports"]==[9099]; assert s["mobile_monitor_restart_via_bootstrap"] is True
