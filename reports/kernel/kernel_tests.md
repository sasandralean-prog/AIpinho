# Kernel Tests

Validation commands:

`python -m pytest tests\unit\test_runtime_kernel_kr.py -q`

Result: 6 passed.

`python -m pytest tests\unit\test_runtime_kernel_kr.py tests\unit\test_runtime_telemetry_ob1.py tests\unit\test_runtime_metrics_ob2.py tests\unit\test_runtime_dashboard_ob3.py tests\unit\test_cognitive_policy_engine_cg1.py tests\unit\test_cognitive_router_cg2.py tests\unit\test_cognitive_escalation_cg3.py tests\unit\test_cognitive_governance_controller_cg4.py -q`

Result: 45 passed.
