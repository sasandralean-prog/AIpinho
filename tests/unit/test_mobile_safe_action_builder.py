from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder


def test_restart_allowed_ports_and_blocked_monitor_port():
    builder = MobileSafeActionBuilder()

    assert builder.restart_port(9088).enabled is True
    assert builder.restart_port(9089).enabled is True
    assert builder.restart_port(9098).enabled is True
    blocked = builder.restart_port(9099)
    assert blocked.enabled is False
    assert blocked.disabled_reason
    assert blocked.side_effect is True


def test_copy_action_is_sanitized_and_low_risk():
    action = MobileSafeActionBuilder().copy("card_x")

    assert action.kind == "copy"
    assert action.risk == "low"
    assert action.side_effect is False
    assert action.endpoint_ref == "/api/v1/mobile/view-model/cards/card_x/copy"

