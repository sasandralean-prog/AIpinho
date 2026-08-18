# Artifact Lifecycle Trace

Trace endpoint:

`GET /api/v1/artifact-library/{artifact_id}/trace`

The trace includes:

- status;
- origin type;
- evidence refs;
- tool invocation ids;
- policy decision ids;
- sanitized metadata.

Debugger surfaces should filter by `artifact_id`, `origin_type`, `sandbox_task_id`, `template_execution_id`, `promotion_plan_id` and `skill_execution_id`.
