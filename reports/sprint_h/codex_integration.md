# Codex Integration

Codex integration path:

1. Create or receive a `task_run_id` through existing governed task creation flow.
2. Poll `GET /api/v1/task_runs/{task_run_id}`.
3. Poll `GET /api/v1/task_runs/{task_run_id}/events` for timeline increments.
4. Poll `GET /api/v1/task_runs/{task_run_id}/artifacts` for outputs.
5. Poll `GET /api/v1/task_runs/{task_run_id}/summary` for compact state.

No Codex-specific runtime endpoint was added.

Codex is treated as a client of the Universal Task Session.

