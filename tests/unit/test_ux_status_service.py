from aipinho.services.ux.ux_status_service import UXStatusService
def test_ux_status_loads_hardening_flags():
    s=UXStatusService().status(); assert s.enabled; assert s.features["raw_viewer_enabled"] is True
