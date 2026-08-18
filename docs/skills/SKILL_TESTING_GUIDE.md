# Skill Testing Guide

Focused tests:

```powershell
python -m pytest tests\skills -q
python -m pytest tests\integration\test_skill_system_api.py -q
python -m pytest tests\multi_agent\skills -q
```

Multi-agent suite:

```powershell
python tests\multi_agent\run_multi_agent_regression.py --skills
```

Test expectations:

- valid manifests pass;
- secret-like manifests fail;
- source-readonly write declarations fail;
- disabled skills cannot execute;
- missing capabilities block execution;
- successful skills produce policy decisions, tool invocations and evidence refs;
- raw remains hidden by default.
