from aipinho.services.ux.ux_latency_service import UXLatencyService
def test_latency_indicator_degrades_slow_target():
    assert UXLatencyService().indicator("9088",2000).state=="degraded"
