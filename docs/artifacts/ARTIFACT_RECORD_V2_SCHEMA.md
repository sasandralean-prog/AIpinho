# ArtifactRecordV2 Schema

`ArtifactRecordV2` normalizes older and newer artifact records into a single operational contract.

Core fields:

- `artifact_id`
- `filename`
- `content_type`
- `size_bytes`
- `status`
- `artifact_type`
- `origin_type`
- `session_id`
- `run_id`
- `agent_id`
- `sandbox_task_id`
- `skill_execution_id`
- `autopilot_run_id`
- `promotion_plan_id`
- `template_execution_id`
- `validation_id`
- `evidence_refs`
- `download_endpoint`
- `requires_token`
- `preview_available`
- `context_usable`
- `retention_policy`

`ready` requires an existing file. Missing files are repaired to `failed` with `artifact_file_missing`.
