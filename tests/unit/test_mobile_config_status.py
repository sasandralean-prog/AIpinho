from aipinho.services.mobile.mobile_status_service import MobileStatusService
def test_mobile_status_flags():
    s=MobileStatusService().status(); assert s["mobile_app_enabled"] and s["token_hardcoded"] is False
