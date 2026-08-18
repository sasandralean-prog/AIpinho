from aipinho.services.regression.regression_harness_service import RegressionHarnessService

def test_regression_status_is_safe():
    status = RegressionHarnessService().status()
    assert status.enabled is True
    assert status.side_effects_allowed is False
