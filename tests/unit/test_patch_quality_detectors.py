from aipinho.services.patching.quality.hardcode_detector import HardcodeDetector
from aipinho.services.patching.quality.policy_bypass_detector import PolicyBypassDetector
from aipinho.services.patching.quality.security_regression_detector import SecurityRegressionDetector


def test_hardcode_detector_rejects_critical_operational_hardcode():
    diff = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a='x'\n+a='C:\\PinhoabacaxiAI'\n"
    result = HardcodeDetector().detect(diff)
    assert result.status == "rejected"
    assert result.critical_found == 1


def test_policy_bypass_detector_rejects_apply_enabled_true():
    diff = "--- a/config.yaml\n+++ b/config.yaml\n@@ -1 +1 @@\n-apply_enabled: false\n+apply_enabled: true\n"
    result = PolicyBypassDetector().detect(diff)
    assert result.status == "rejected"
    assert result.bypass_signals == 1


def test_security_regression_detector_blocks_removed_quality_gate():
    diff = "--- a/policy.py\n+++ b/policy.py\n@@ -1 +1 @@\n-quality_gate = True\n+quality = True\n"
    result = SecurityRegressionDetector().detect(diff)
    assert result.status == "rejected"
    assert result.regression_signals == 1
