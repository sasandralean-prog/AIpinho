# Retrieval Source Registry

All retrieval sources are declared in `config/rag/retrieval_source_registry.yaml`. An adapter that is not registered is blocked.

| Source | Adapter | Scope | Notes |
| --- | --- | --- | --- |
| `project_files` | `file_retrieval_source` | workspace | Uses the read-only execution sandbox and explicit paths. |
| `project_reports` | `project_report_retrieval_source` | project/report | Reads local Markdown reports only. |
| `task_results` | `task_result_retrieval_source` | task run | Requires `run_id` and exposes the sanitized task summary. |
| `validation_results` | `validation_result_retrieval_source` | validation | Requires `validation_id` and exposes display-safe findings. |
| `patch_apply_results` | `patch_apply_result_retrieval_source` | patch apply | Requires `apply_run_id` and exposes result metadata, not file content. |
| `curated_memory` | `curated_memory_retrieval_source` | curated memory | Requires an explicit request and only reads active approved memory. |

Blocked registry entries:

- `legacy_vectorstore`
- `web`
- `raw_logs`

Adding a source requires a registry entry, policy, adapter, scope rule, citation type, tests and status visibility.
