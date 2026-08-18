# Project Generation Contracts

Project generation uses `ProjectGenerationRequest` and `ProjectGenerationResult`.

Important request fields:

- `user_goal`
- `project_name`
- `project_type`
- `sandbox_workspace_id`
- `sandbox_task_id`
- `artifact_requested`
- `output_zip_name`
- `requested_assets`
- `requested_features`
- `validation_level`

Important result fields:

- `project_generation_id`
- `sandbox_task_id`
- `status`
- `project_root`
- `project_name`
- `project_type`
- `files_created`
- `assets_created`
- `validation_ids`
- `artifact_ids`
- `zip_artifact_id`
- `download_endpoint`
- `requires_token`
- `final_answer_sanitized`
- `evidence_refs`
- `warnings`
- `errors`

Statuses:

- `queued`
- `running`
- `validation_failed`
- `artifact_failed`
- `completed`
- `completed_with_warnings`
- `blocked`
- `failed`
- `cancelled`
- `timed_out`

The contract separates sandbox generation from workspace mutation. A generated ZIP artifact is not a write into the requested project unless a future explicit workspace write contract asks for it.

