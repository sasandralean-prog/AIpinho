# Project Trace Filters

Debugger 2.0 can filter by:

- `project_profile_id`
- `workspace_profile_id`
- `validation_profile_id`
- `command_profile_id`
- `agent_id`
- `run_id`
- `tool_invocation_id`
- `artifact_id`

Events emitted by Tool Gateway include project context as sanitized payload and `project:{project_profile_id}` evidence ref when available.

