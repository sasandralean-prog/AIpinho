# Sandbox Workspace Schema

`SandboxWorkspace` fields:
- `sandbox_workspace_id`
- `name`
- `role`
- `root_path_sanitized`
- `created_at`
- `metadata_sanitized`

Roles are `sandbox_mutable`, `sandbox_readonly`, `sandbox_artifact` and `sandbox_tmp`.

`SandboxTask` links work to one workspace and carries status, owner agent, timestamps, evidence refs and sanitized metadata.
