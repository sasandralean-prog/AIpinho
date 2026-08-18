# Dashboard Alignment

Universal dashboard contract:

- Any dashboard client must use `/api/v1/task_runs` and `/api/v1/task_runs/{run_id}` for task execution state.
- No dashboard-only runtime state endpoint was created.
- No Codex/Gemini/Mobile-specific endpoint was created.

Backend verification:

- App factory mounted:
  - `/api/v1/task_runs`
  - `/api/v1/task_runs/{run_id}`
  - `/api/v1/task_runs/{run_id}/events`
  - `/api/v1/task_runs/{run_id}/artifacts`
  - `/api/v1/task_runs/{run_id}/summary`

Desktop UI note:

- Existing launcher/dashboard screens can be wired to these endpoints without another runtime adapter. This sprint establishes the canonical backend protocol and avoids adding a dashboard-specific fork.

