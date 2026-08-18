# Sprint H Regression Candidates

Regression tests added:

- Universal session derives progress from real plan steps.
- Completed result maps to `COMPLETED` and 100 percent progress.
- Waiting approval exposes approval id, status and actions.
- Missing outputs prevent `safe_to_report_success`.
- Artifact refs from TaskRunResult are surfaced in artifact state.
- Event polling supports `after_sequence`.
- HTTP endpoints expose universal session, events, artifacts, summary and list.

Recommended future tests:

- End-to-end task creation then universal polling.
- Mobile UI rendering of universal task session progress.
- Launcher/dashboard rendering of universal task session progress.
- Artifact registry enrichment for multiple artifact providers.
- SSE/realtime bridge consuming the same session event stream.

