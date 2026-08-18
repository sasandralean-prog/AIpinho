# FireTest 5 H1B4.3.3a ProjectAnalysis Zero-Progress Timeout Forensics

Generated at: 2026-08-12T11:43:41.8746853-03:00

## Verdict

FIRETEST5_H1B4_3_3A_PROJECT_ANALYSIS_TIMEOUT_EXPLAINED

ProjectAnalysis did not recover enough to reach artifact_creation_started. The apparent zero-progress timeout is now explained and no longer appears as zero progress in the final public diagnostic.

Final observed frontier: PROJECT_ANALYSIS_FILE_READ_TIMEOUT_BEFORE_ARTIFACT_RENDER

## Objective

Isolate why the public FireTest 5 path previously reported PROJECT_ANALYSIS_TIMEOUT after about 46s while files_scanned, files_read, and bytes_read were all zero.

## Scope And Non-Goals

- No FIRETEST5_READY attempt.
- No H1B5.
- No sidecar work.
- No metadata changes.
- No Validation, Completion, or Speaker Truth relaxation.
- No timeout increase as a solution.

## Root Cause

The previous zero-progress symptom was an instrumentation boundary problem, not proof that no work happened.

ProjectAnalysisService called ProjectTreeService.build_tree_summary and FileContextBuilder.build_context as monolithic operations. If budget was exceeded inside or immediately after one of those calls, the exception handler created a blocked ProjectAnalysisResult without preserving partial tree/context state or checkpoint counters. That caused legacy counters to remain zero even when work had already occurred.

The final public run shows the concrete blocker:

- reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- blocking_operation: file_read
- last_checkpoint: after_file_read_item
- last_completed_checkpoint: after_file_read_item
- budget_exceeded_at: after_file_read_item
- current_path_sample: src/main/kotlin/com/pinhoabacaxi/musicasdesktop/audio/dsp/DesktopEqualizerTemplateJsonCodec.kt

## Metrics Before And After

Before H1B4.3.3a, the public diagnostic showed:

- reason_code: PROJECT_ANALYSIS_TIMEOUT
- checkpoint: after_file_read_batch
- duration_ms: about 46390
- files_scanned: 0
- files_read: 0
- bytes_read: 0
- artifact_creation_started_count: 0

After H1B4.3.3a, the final public diagnostic showed:

- reason_code: PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- duration_ms: 20812
- files_discovered: 76
- files_scan_attempted: 127
- files_scanned: 78
- files_read: 3
- bytes_read: 17214
- artifact_creation_started_count: 0

Checkpoint timing:

| Checkpoint | Elapsed ms |
|---|---:|
| before_path_resolution | 0 |
| after_path_resolution | 0 |
| before_workspace_root_scan | 15 |
| after_workspace_root_scan | 15 |
| before_file_enumeration | 15 |
| during_file_enumeration | 3108 |
| after_file_enumeration | 3125 |
| before_file_selection | 3125 |
| after_file_selection | 18702 |
| before_file_read_batch | 18702 |
| before_file_read_item | 19327 |
| after_file_read_item | 20812 |

Interpretation: the expensive region is not path resolution and not root scan. The run spent most time across file selection and file read. It timed out after reading item checkpoints, before ProjectAnalysis could safely hand control to artifact rendering.

## Implementation

Files changed:

- src/aipinho/schemas/analysis/project_analysis_result.py
- src/aipinho/services/analysis/project_analysis_service.py
- src/aipinho/services/analysis/project_tree_service.py
- src/aipinho/services/analysis/file_context_builder.py
- src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- tests/unit/test_project_analysis_service.py
- tests/unit/test_project_analysis_public_boundary.py

Implemented changes:

- Added ProjectAnalysisResult forensic fields: last_checkpoint, last_completed_checkpoint, elapsed_ms_by_checkpoint, files_discovered, files_scan_attempted, current_root, current_path_sample, blocking_operation, budget_exceeded_at.
- Added cooperative progress callbacks to ProjectTreeService for path resolution, root scan, and file enumeration.
- Added cooperative progress callbacks to FileContextBuilder before/after batch and item reads.
- Replaced generic PROJECT_ANALYSIS_TIMEOUT with stage-specific reason codes.
- Preserved partial metrics in blocked ProjectAnalysisResult even when the blocking call does not return a full context object.
- Propagated ProjectAnalysis forensic fields through ReadonlyAnalysisArtifactRuntimeService boundary details and project_analysis terminal events.

## Public Rerun

- session_id: firetest5_h1b4_3_3a_public_diagnostic_final_20260812
- task_run_id: task_run_af8c86a69ed54021866cdb7a02129b84
- operation_id: op_687d0e9f0a954dfd80b1f045e9229f48
- client_response_status: 200
- client_response_time_ms: 222309
- server_final_status: BLOCKED
- run.status: blocked
- result.status: blocked
- finished_at: 2026-08-12T14:40:52.896223+00:00

Budget snapshot:

- ProjectAnalysis max_total_seconds: 20.0
- ProjectAnalysis max_files_scanned: 5000
- ProjectAnalysis max_files_read: 80
- ProjectAnalysis max_bytes_read: 2000000
- Phase1 max_runtime_seconds: 120.0
- ArtifactRender max_artifact_seconds: 60.0

Phase 0 / CVL:

- status: ready
- result_id: cvl_result_5b7aa6d50ad94903972af297a5a4e35e
- output directory: reports/runtime_consolidation/firetest5_h1b4_3_3a_phase0_cvl/

## Runtime Safety

- terminal_event_count: 1
- first_terminal_event: run_blocked, sequence 10, reason PROJECT_ANALYSIS_FILE_READ_TIMEOUT
- artifact_creation_started_count: 0
- artifact_created_count: 0
- artifact_created_after_terminal_count: 0
- artifact_late_rejected_count: 0
- artifact endpoint status: blocked_before_artifact_creation
- artifact index status: absent

Post-terminal events:

| Sequence | Type | Status | Message |
|---:|---|---|---|
| 11 | terminalization_already_applied | ignored | Terminalization ignored because the TaskRun already has a terminal event. |
| 12 | terminalization_already_applied | ignored | Terminalization ignored because the TaskRun already has a terminal event. |

Event sequence:

| Sequence | Type | Status | Message |
|---:|---|---|---|
| 1 | run_created | created | TaskRun created without execution. |
| 2 | task_bootstrap_created | created | Universal Task identity created before execution. |
| 3 | PlanningStarted | planning | Canonical planning started before execution. |
| 4 | PlanningFinished | planned | Canonical planning finished. |
| 5 | ExecutionPlanCreated | ready | Canonical ExecutionPlan created as execution boundary. |
| 6 | run_queued | queued | Read-only artifact analysis queued. |
| 7 | run_started | running | Read-only artifact analysis started. |
| 8 | project_analysis_started | running | Project analysis started. |
| 9 | project_analysis_budget_exceeded | timeout | Project analysis budget exceeded during after_file_read_item. |
| 10 | run_blocked | blocked | Project analysis budget exceeded during after_file_read_item. |
| 11 | terminalization_already_applied | ignored | Terminalization ignored because the TaskRun already has a terminal event. |
| 12 | terminalization_already_applied | ignored | Terminalization ignored because the TaskRun already has a terminal event. |

## Validation / Completion / Speaker Truth

- validation.status: blocked
- completion.status: blocked
- speaker_truth.safe_to_report_success: False

These remained correctly blocked. No partial ProjectAnalysis result was treated as Validation PASS, and no artifact absence was hidden.

## Tests Executed

- python -m pytest tests/unit/test_project_analysis_service.py tests/unit/test_project_analysis_public_boundary.py tests/contract/test_analysis_contracts.py tests/unit/test_readonly_analysis_phase1_budgets.py tests/unit/test_task_run_store.py tests/unit/test_universal_task_session_service.py -q
- Result: 36 passed in 67.06s
- python -m py_compile src/aipinho/schemas/analysis/project_analysis_result.py src/aipinho/services/analysis/project_analysis_service.py src/aipinho/services/analysis/project_tree_service.py src/aipinho/services/analysis/file_context_builder.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- Result: PASS

## Remaining Gaps

- ProjectAnalysis still does not cross the public path under the configured 20s budget.
- File selection consumed a large part of the budget window before file reading.
- Artifact render terminality was not exercised in this final run because ProjectAnalysis blocked before artifact_creation_started.
- Public Chat still responds synchronously after a long wait rather than returning accepted_running or an early governed timeout boundary.
- The repository copy at C:/Dev/AIpinho is not a git repository, so git status/diff could not be used for final changed-file verification.

## Recommendation

Do not advance to H1B5 yet.

The next practical wave should target either:

1. ProjectAnalysis file selection/read budget cooperation, because the public path now reaches file_read and times out specifically there.
2. Public Chat accepted_running / governed response boundary, because the client still waited more than 220s for a blocked response.

After ProjectAnalysis crosses again in the public process, repeat FireTest 5 diagnostic H1B4.3.3 to validate artifact render terminality on the real artifact path.

## Evidence Files

- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_budgets.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_phase0_cvl.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_request.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_chat_response.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_endpoint_summary.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_endpoint_truth.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_endpoint_events.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_endpoint_artifacts.json
- reports/runtime_consolidation/firetest5_h1b4_3_3a_public_diagnostic_final_collected.json
- data/runtime/task_runs/task_run_af8c86a69ed54021866cdb7a02129b84/run.json
- data/runtime/task_runs/task_run_af8c86a69ed54021866cdb7a02129b84/result.json
- data/runtime/task_runs/task_run_af8c86a69ed54021866cdb7a02129b84/events.json
