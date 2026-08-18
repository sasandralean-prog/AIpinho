# Testing and Regression Guide

## Fast Gate

```powershell
python tests\multi_agent\run_multi_agent_regression.py --quick
```

## Available Full Gate

```powershell
python tests\multi_agent\run_multi_agent_regression.py --all
```

## What Normal Tests Must Not Do

- Call real LLM providers.
- Use real API keys.
- Mutate user workspaces.
- Run destructive shell.
- Depend on internet.

## Manual Gates

Use manual/provider smoke only when explicitly configured. Keep those tests separate from the normal regression battery.

## Sprint 20 Dogfood Addendum

Use controlled dogfood fixtures to prove that the system can do real work while keeping policy boundaries intact.

Required evidence for this class of test:

- source-readonly read succeeds;
- source-readonly write is denied;
- target-mutable write succeeds only through governed tools;
- shell runs with explicit workspace context;
- validation is recorded;
- artifacts are registered with token-protected download endpoints;
- mobile/launcher state agrees with run status.

Focused commands used in Sprint 20:

```text
python -m py_compile src\aipinho\services\agents\agent_session_kernel_service.py
python -m pytest tests\unit\test_agent_session_kernel_service.py -q --tb=short
python -m pytest tests\unit\test_agent_tool_gateway_service.py -q --tb=short
python -m pytest tests\multi_agent\golden_paths\test_multi_agent_golden_paths.py -q --tb=short
python tests\multi_agent\run_multi_agent_regression.py --quick
```

When adding future dogfood tests, prefer reusable workspace roles and generic fixtures over prompt or project-specific branches.

## RC3 Operational Regression

Minimum RC3 gates:

```text
python tests\multi_agent\run_multi_agent_regression.py --quick
python tests\multi_agent\run_multi_agent_regression.py --security
python tests\multi_agent\run_multi_agent_regression.py --speaker-truth
```

Optional gates should be run when available:

```text
python tests\multi_agent\run_multi_agent_regression.py --freedom
python tests\multi_agent\run_multi_agent_regression.py --ui-contracts
python tests\multi_agent\run_multi_agent_regression.py --artifacts
python tests\multi_agent\run_multi_agent_regression.py --all
```

If a selected gate is unsupported by the runner, document it as unsupported instead of reporting it as passed.
