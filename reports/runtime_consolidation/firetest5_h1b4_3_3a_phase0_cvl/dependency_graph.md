# CVL - Dependency Graph

## Graph

- Graph: `dependency_graph_cb002e57709a48bf9d8b8d28ff6a7718`
- Profile: `firetest5_h1b4_3_3a_project_analysis_zero_progress_timeout`

| Node | Type | Depends On | Dependents |
| --- | --- | --- | --- |
| `pipeline:public_chat_boundary` | `pipeline` | `contract:analysis_readonly, contract:task_run_terminality, contract:project_analysis_forensics` | `pipeline:task_run_bootstrap` |
| `pipeline:task_run_bootstrap` | `pipeline` | `pipeline:public_chat_boundary` | `pipeline:project_analysis_boundary` |
| `pipeline:project_analysis_boundary` | `pipeline` | `pipeline:task_run_bootstrap` | `pipeline:project_analysis_checkpoints` |
| `pipeline:project_analysis_checkpoints` | `pipeline` | `pipeline:project_analysis_boundary` | `pipeline:terminal_event_idempotency` |
| `pipeline:terminal_event_idempotency` | `pipeline` | `pipeline:project_analysis_checkpoints` | `pipeline:validation` |
| `pipeline:validation` | `pipeline` | `pipeline:terminal_event_idempotency, capability:read_workspace` | `pipeline:speaker_truth` |
| `pipeline:speaker_truth` | `pipeline` | `pipeline:validation` | `` |
| `contract:analysis_readonly` | `contract` | `` | `pipeline:public_chat_boundary` |
| `contract:task_run_terminality` | `contract` | `` | `pipeline:public_chat_boundary` |
| `contract:project_analysis_forensics` | `contract` | `` | `pipeline:public_chat_boundary` |
| `module:projectanalysisservice` | `module` | `` | `` |
| `module:projecttreeservice` | `module` | `` | `` |
| `module:filecontextbuilder` | `module` | `` | `` |
| `module:readonlyanalysisartifactruntimeservice` | `module` | `` | `` |
| `module:taskrunstore` | `module` | `` | `` |
| `capability:read_workspace` | `capability` | `` | `pipeline:validation` |
