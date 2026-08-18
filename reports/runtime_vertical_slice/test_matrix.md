# Runtime Vertical Slice Test Matrix

Date: 2026-07-05

## Automated Tests

Command:

```powershell
python -m pytest tests/governance/test_runtime_vertical_slice.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py::test_readonly_sapoandando_prompt_overrides_legacy_patch_signal tests/governance/test_lifecycle_core.py::test_readonly_governance_diagnostic_does_not_become_project_bootstrap tests/governance/test_lifecycle_core.py::test_planning_readonly_existing_good_case_stays_readonly -q
```

Result:

```text
22 passed in 89.55s
```

## Coverage

- Read-only artifact request creates TaskRun and artifacts.
- Source workspace files remain unchanged.
- Phase 2 blocks when previous artifacts are missing.
- Phase 2 consumes real Phase 1 artifacts when present.
- Lifecycle expected outputs allow Speaker Truth success only when all outputs exist.
- Existing read-only no-artifact behavior remains no-task/no-approval.

## Checkpoint

TEST_MATRIX_READY
