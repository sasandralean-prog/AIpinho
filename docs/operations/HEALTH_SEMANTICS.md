# Health Semantics

## Endpoint

- `GET /api/v1/health/semantics`

## Separate Meanings

- `backend_health`: HTTP/backend liveness.
- `operational_health`: whether common governed flows can execute.
- `observability_health`: whether traces/runs/events/dashboard are clean and consistent.

## Important Distinction

`observability_health=degraded` does not mean the backend is offline. It means runtime evidence has warnings, blocked runs, stale state or trace inconsistency.

Mobile and Launcher should avoid mapping observability degradation directly to "Backend offline".
