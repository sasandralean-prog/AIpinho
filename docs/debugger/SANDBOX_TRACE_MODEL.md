# Sandbox Trace Model

Endpoint: `GET /api/v1/sandbox/tasks/{sandbox_task_id}/trace`.

Trace events include task creation/cancellation, file operations, shell completion/block, artifact export and cleanup. Tool Gateway events also carry `sandbox_task_id`, `sandbox_workspace_id`, `relative_path`, `cwd_inside_sandbox` and `operation_scope`.
