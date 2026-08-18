# Mobile Alignment

Implemented alignment:

- `PipelineMobileAggregator` now attaches `universal_task_session` to the task state card metadata.
- The card exposes the canonical polling endpoints:
  - `/api/v1/task_runs/{task_run_id}`
  - `/api/v1/task_runs/{task_run_id}/events`
  - `/api/v1/task_runs/{task_run_id}/artifacts`

Result:

- Mobile pipeline no longer needs to invent progress for task state.
- Mobile can poll the universal session for status, phase, progress, approval, validation, artifacts and result.

UI note:

- This sprint changed the backend view-model payload. A future native Android visual iteration can choose how to render the new fields, but must use the same endpoints.

