# Universal Polling

External task polling endpoints:

- `GET /api/v1/external/tasks/{external_task_id}`
- `GET /api/v1/external/tasks/{external_task_id}/progress`
- `GET /api/v1/external/tasks/{external_task_id}/summary`
- `GET /api/v1/external/tasks/{external_task_id}/artifacts`

These endpoints reuse Sprint H:

- `UniversalTaskSessionService`
- `/api/v1/task_runs/{task_run_id}`
- `/api/v1/task_runs/{task_run_id}/events`
- `/api/v1/task_runs/{task_run_id}/artifacts`
- `/api/v1/task_runs/{task_run_id}/summary`

No external client needs internal logs or task store access.

