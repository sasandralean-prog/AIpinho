# Universal Task Session

Implemented files:

- `src/aipinho/schemas/runtime/universal_task_session.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`

Public fields implemented:

- `task_run_id`
- `status`
- `phase`
- `progress`
- `eta`
- `started_at`
- `updated_at`
- `current_step`
- `approval_state`
- `validation_state`
- `artifact_state`
- `result_state`
- `events_count`
- `links`

Universal endpoints:

- `GET /api/v1/task_runs`
- `GET /api/v1/task_runs/{run_id}`
- `GET /api/v1/task_runs/{run_id}/events`
- `GET /api/v1/task_runs/{run_id}/artifacts`
- `GET /api/v1/task_runs/{run_id}/summary`

Compatibility aliases:

- `GET /api/v1/task-runs/{run_id}/session`
- `GET /api/v1/task-runs/{run_id}/artifacts`
- `GET /api/v1/task-runs/{run_id}/summary`

Legacy raw endpoints were preserved to avoid breaking existing clients.

