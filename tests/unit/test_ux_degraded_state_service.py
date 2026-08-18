from aipinho.services.ux.ux_degraded_state_service import UXDegradedStateService
def test_backend_down_becomes_degraded_state():
    states=UXDegradedStateService().consolidate({"backend":"down"}); assert states and states[0].state=="offline"
