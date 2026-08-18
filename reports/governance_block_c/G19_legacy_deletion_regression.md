# G19 - Legacy Deletion Regression

Status: G19_LEGACY_DELETION_REGRESSION_READY

Generated UTC: 2026-06-26T10:32:19.629848+00:00

## Deleted

- `quarantine/legacy/governance/2026-06-26/config/runtime/runtime_profiles.yaml`

## Kept archived

- `quarantine/legacy/governance/2026-06-26/src/aipinho/api/routers/chat_router.py`
- `quarantine/legacy/governance/2026-06-26/src/aipinho/api/routers/continue_integration_router.py`

## Regression

Focused regression after quarantine and deletion:

```text
35 passed in 84.18s
```

Validated:

- public chat route survives;
- persistent chat route survives;
- OpenAI-compatible Continue route survives;
- VSCode Continue action preview/execute routes are canonical first;
- planning readonly stays readonly;
- workspace query stays read-only/canonical;
- quarantine files are not imported.

