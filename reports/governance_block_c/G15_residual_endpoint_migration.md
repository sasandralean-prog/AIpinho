# G15 - Residual Endpoint Migration

Status: G15_RESIDUAL_ENDPOINT_MIGRATION_READY

Generated UTC: 2026-06-26T10:32:19.629848+00:00

## Migrated surfaces

- `GET /api/v1/chat/status`
- `GET /api/v1/chat/diagnostics`
- `GET /api/v1/chat/model-status`
- `POST /api/v1/chat/manual-inference/preview`
- `POST /api/v1/chat/manual-inference`
- `POST /v1/integrations/vscode/actions/preview`
- `POST /v1/integrations/vscode/actions/execute`

## Canonical behavior

- Continue action preview now uses `CanonicalPublicChatService` and returns canonical lifecycle metadata.
- Continue action execute records approval decision only when `approval_id` is provided; it does not write files or run shell directly.
- Manual inference remains a specialized model executor endpoint, now owned by `governance_lifecycle_router`.
- Chat status/model status are read/status endpoints owned by the canonical router.

## Tests

- `tests/governance/test_g15_residual_endpoint_migration.py`

Result: passed in focused regression.
