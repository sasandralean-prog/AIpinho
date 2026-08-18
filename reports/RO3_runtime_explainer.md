# RO3 Runtime Explainer

Status: RO3_RUNTIME_EXPLAINER_READY

Implemented:

- `RuntimeExplainerService`
- `RuntimeExplanation`
- advisory explanation endpoint

Endpoint:

- `POST /api/v1/runtime/doctor/explain`

Operational limits:

- does not decide;
- does not approve;
- does not execute;
- does not patch;
- does not mutate runtime state.

Recommended model profile:

- `qwen2.5-7b-instruct`

The current implementation keeps tests deterministic and preserves read-only behavior.

Verification:

- `tests\unit\test_runtime_operator_ro.py` verifies the explainer does not decide execution and does not generate patches.
- Regression slice: 48 passed.
