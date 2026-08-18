# OB1 Runtime Telemetry

Status: RUNTIME_TELEMETRY_READY.

## Scope

Implemented the first Runtime telemetry layer as an observer-only service.

## Files

- `src/aipinho/schemas/telemetry/event.py`
- `src/aipinho/services/telemetry/runtime_telemetry_service.py`
- `src/aipinho/api/routers/telemetry_router.py`
- `src/aipinho/api/routers/__init__.py`
- `tests/unit/test_runtime_telemetry_ob1.py`
- `docs/observability/runtime_telemetry.md`

## Invariants

- No Runtime behavior mutation.
- Correlation by `correlation_id`, `session_id`, `task_run_id`, and `task_id`.
- Structured query and session views.
- Legacy telemetry events endpoint preserved.

## Verification

- `python -m pytest tests\unit\test_runtime_telemetry_ob1.py -q`
  - Result: 5 passed.
- `python -m compileall src\aipinho\schemas\telemetry\event.py src\aipinho\services\telemetry\runtime_telemetry_service.py src\aipinho\api\routers\telemetry_router.py src\aipinho\api\routers\__init__.py`
  - Result: passed.
- `python -m pytest tests\unit\test_runtime_telemetry_ob1.py tests\unit\test_cognitive_policy_engine_cg1.py tests\unit\test_cognitive_router_cg2.py tests\unit\test_cognitive_escalation_cg3.py tests\unit\test_cognitive_governance_controller_cg4.py -q`
  - Result: 29 passed.
- Router registration check:
  - Router count: 136.
  - `/api/v1/runtime/telemetry` registered: true.
  - `/api/v1/telemetry` compatibility router registered: true.

## Verdict

RUNTIME_TELEMETRY_READY
