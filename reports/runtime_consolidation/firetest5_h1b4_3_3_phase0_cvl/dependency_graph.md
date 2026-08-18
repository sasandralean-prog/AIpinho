# CVL - Dependency Graph

## Graph

- Graph: `dependency_graph_b18e977e605a4ce4a76b717f63ef87fb`
- Profile: `firetest5_h1b4_3_3_public_diagnostic_phase0`

| Node | Type | Depends On | Dependents |
| --- | --- | --- | --- |
| `pipeline:public_chat_boundary` | `pipeline` | `contract:analysis_readonly, contract:artifact_runtime, contract:task_run_terminality` | `pipeline:task_run_bootstrap` |
| `pipeline:task_run_bootstrap` | `pipeline` | `pipeline:public_chat_boundary` | `pipeline:project_analysis_boundary` |
| `pipeline:project_analysis_boundary` | `pipeline` | `pipeline:task_run_bootstrap` | `pipeline:artifact_render_budget` |
| `pipeline:artifact_render_budget` | `pipeline` | `pipeline:project_analysis_boundary` | `artifact:reports_firetest5_phase1_discovery_md, artifact:reports_firetest5_project_inventory_md, artifact:reports_firetest5_music_inventory_csv, artifact:reports_firetest5_evidence_phase1_zip, pipeline:terminal_event_idempotency` |
| `pipeline:terminal_event_idempotency` | `pipeline` | `pipeline:artifact_render_budget` | `pipeline:artifact_index` |
| `pipeline:artifact_index` | `pipeline` | `pipeline:terminal_event_idempotency` | `pipeline:validation` |
| `pipeline:validation` | `pipeline` | `pipeline:artifact_index, capability:read_workspace, capability:artifact_render_budget, capability:terminal_event_idempotency` | `pipeline:speaker_truth` |
| `pipeline:speaker_truth` | `pipeline` | `pipeline:validation` | `` |
| `contract:analysis_readonly` | `contract` | `` | `pipeline:public_chat_boundary` |
| `contract:artifact_runtime` | `contract` | `` | `pipeline:public_chat_boundary` |
| `contract:task_run_terminality` | `contract` | `` | `pipeline:public_chat_boundary` |
| `module:readonly_analysis_artifact_runtime` | `module` | `` | `` |
| `module:task_run_store` | `module` | `` | `` |
| `module:universal_task_session_service` | `module` | `` | `` |
| `module:artifact_runtime_service` | `module` | `` | `` |
| `capability:read_workspace` | `capability` | `` | `pipeline:validation` |
| `capability:artifact_render_budget` | `capability` | `` | `pipeline:validation` |
| `capability:terminal_event_idempotency` | `capability` | `` | `pipeline:validation` |
| `artifact:reports_firetest5_phase1_discovery_md` | `artifact` | `pipeline:artifact_render_budget` | `` |
| `artifact:reports_firetest5_project_inventory_md` | `artifact` | `pipeline:artifact_render_budget` | `` |
| `artifact:reports_firetest5_music_inventory_csv` | `artifact` | `pipeline:artifact_render_budget` | `` |
| `artifact:reports_firetest5_evidence_phase1_zip` | `artifact` | `pipeline:artifact_render_budget` | `` |
