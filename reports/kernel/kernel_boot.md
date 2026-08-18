# KR1 Kernel Boot

Status: KR1_READY.

The Runtime Kernel boots in `INIT`, registers canonical modules, validates dependencies, and transitions to `READY` when no module is blocked.

Invariants:

- Modules must be registered before dispatch.
- Kernel does not interpret prompts.
- Kernel does not execute models or tools.
- Kernel only coordinates state, contracts, events, modules, and dispatch eligibility.

Validation:

- `python -m pytest tests\unit\test_runtime_kernel_kr.py -q`
  - Result: 6 passed.
