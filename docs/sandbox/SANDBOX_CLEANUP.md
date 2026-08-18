# Sandbox Cleanup

Cleanup is two-stage:
1. `POST /api/v1/sandbox/cleanup/preview`
2. `POST /api/v1/sandbox/cleanup/apply`

Only aged files under sandbox `tmp` and `trash` become candidates. Workspaces, task traces, reports and registered artifacts are not cleanup targets. Apply without a valid preview is blocked with `sandbox_cleanup_requires_preview`.
