# Runtime State Hygiene

## Purpose

Runtime cleanup must reduce stale dashboard noise without deleting operational evidence.

## Official Endpoints

- `GET /api/v1/runtime/hygiene/status`
- `POST /api/v1/runtime/hygiene/preview`
- `POST /api/v1/runtime/hygiene/apply/{preview_id}`

## Rules

- Preview is required before apply.
- Apply never deletes evidence.
- Active stale runs are marked `cancelled` with `stale_runtime_cleanup`.
- Old sessions can be archived.
- Applied cleanups are audited under `data/runtime/hygiene`.

## Acceptance Signal

After cleanup, dashboard degraded state should reflect current operational issues, not stale field-trial residue.
