# H1C0.R2.7 — Accepted Running Artifact Worker Terminalization Guard

## Verdict

`FIRETEST5_H1C0_R2_7_ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GUARD_READY`

FireTest 5 remains `NOT_READY`.

The public runtime no longer leaves an accepted worker in limbo after `artifact_creation_started`. The clean Phase 0→6 rerun now produces a terminal TaskRun result, `/result=200`, `finished_at`, and exactly one terminal run event. Phase 1 still blocks, but it blocks as a governed terminal state rather than as an orphaned accepted run.

## Objective

Close the runtime terminality gap observed in H1C0.R2.6:

`accepted_running → artifact_creation_started → no artifact terminal → no result.json → no finished_at → terminal_event_count=0`

The wave was intentionally narrow. It did not reopen metadata sufficiency, root binding, entity selection, relationship truth, or renderer observation.

## Before State

H1C0.R2.6 public run created:

- `task_run_id = task_run_ac1b9a417c6f4da1a739143d28bf42d3`
- `operation_id = op_0a583c02125647568b26a2bfc1e0175c`
- `client_response_status = accepted_running`
- last artifact event: `artifact_creation_started`
- logical artifact: `reports/firetest5/phase1_discovery.md`
- `result.json = missing`
- `/result = 404`
- `finished_at = null`
- `terminal_event_count = 0`

Observed blocker:

`ARTIFACT_RUNTIME_STALLED_AFTER_ARTIFACT_CREATION_STARTED_WITHOUT_TERMINAL_RESULT`

## Diagnosis

The accepted-running public boundary returned to the client while a daemon worker continued artifact runtime execution. The previous lifecycle had no persistent observer able to guarantee terminal state if the worker failed, exited silently, or stalled after `artifact_creation_started`.

Missing pieces before patch:

- no accepted-running worker terminality guard;
- no artifact-specific watchdog after `artifact_creation_started`;
- worker exceptions after public response could be held locally without a guaranteed persisted result;
- worker `finally` restored runtime patches but did not enforce terminal `TaskRunResult`;
- `/result=404` could remain the final externally visible state after artifact start.

Diagnostic report:

`reports/runtime_consolidation/firetest5_h1c0_r2_7_artifact_worker_terminalization_guard_diagnostic.json`

## Changed Files

- `config/runtime/task_run_event_policy.yaml`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/services/cvl/cognitive_readiness_service.py`
- `tests/unit/test_accepted_running_artifact_worker_terminalization_guard.py`
- `tests/unit/test_cvl_artifact_worker_terminalization_frontier.py`

## Worker Lifecycle Model

Added `AcceptedRunningWorkerTerminalityPolicy` and an accepted-running worker guard.

The guard tracks:

- accepted run id;
- worker thread state;
- last artifact creation event;
- artifact terminal events after start;
- existing terminal result;
- existing terminal run event;
- governed cancellation;
- exception/silent-exit/stall reason.

If an accepted worker starts artifact creation and no artifact terminal state or TaskRun result appears, the guard terminalizes the run as blocked/failed with a specific artifact-worker reason. It does not convert the run to success.

## Artifact Creation Watchdog / Guard Behavior

Added guard events to the runtime event policy:

- `artifact_creation_terminalization_guard_started`
- `artifact_creation_terminalization_guard_triggered`
- `artifact_creation_exception_captured`
- `artifact_creation_worker_silent_exit_detected`
- `artifact_creation_terminalization_guard_completed`
- `artifact_creation_terminalization_guard_skipped`

The guard can produce a terminal blocked result for:

- artifact start without terminal artifact/result;
- worker silent exit;
- worker exception after accepted_running;
- artifact creation exception after accepted_running.

## Exception And Silent-Exit Handling

The runtime now converts accepted-worker exceptions into terminal results instead of leaving `/result=404`.

During the clean public rerun, the worker did not remain stalled. It raised an artifact-creation exception after `artifact_creation_started`. The new path emitted:

- `artifact_failed_count = 1`
- `result_json_exists = true`
- `/result = 200`
- `result_reason_code = ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING`
- `terminal_event_count = 1`

This is a correct R2.7 outcome: the worker no longer disappears without a terminal sentence.

## Terminal Result Contract

Every terminal accepted-running worker path now must preserve:

- terminal run status;
- terminal result status;
- `finished_at`;
- validation blocked when artifact runtime fails;
- completion blocked;
- Speaker Truth conservative;
- lightweight artifact/runtime summary;
- one terminal run event.

The acceptable terminal result is blocked or failed, never success, unless the normal governed runtime actually completes.

## Idempotency Behavior

Terminal idempotency was preserved:

- existing semantic result is not overwritten by the guard;
- existing terminal result suppresses guard rewrite;
- existing terminal event is not duplicated;
- governed cancellation suppresses duplicate guard terminalization;
- TaskRunStore conservative repair no longer replaces a more specific artifact/runtime reason with generic `TASKRUN_LIFECYCLE_TIMEOUT`.

Clean rerun result:

- `terminal_event_count = 1`
- `terminal_event_types = [run_failed]`

## Store / Result Persistence

`TaskRunStore.save_result()` now writes `result.json` before projecting terminal run/index state. Reads are lock-protected to avoid Windows read/replace races.

This prevents a run index from becoming terminal before its result exists and reduces the chance of conservative repair observing a half-persisted terminal state.

## Endpoint Behavior

Clean rerun endpoint timings:

- summary: `200`, `2296ms`
- result: `200`, `15ms`
- truth: `200`, `16ms`
- events: `200`, `30ms`
- artifacts: `200`, `16ms`
- session: `200`, `14ms`

The result endpoint is no longer 404 after artifact-start failure.

## Validation / Completion / Speaker Truth

Phase 1 result after R2.7:

- `validation.status = blocked`
- `validation.reason_code = ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING`
- `completion.status = blocked`
- `completion.safe_to_report_success = false`
- `truth.safe_to_report_success = false`

No FireTest success, Phase 1 success, metadata success, or inventory success was claimed.

## Phase Progression

Clean Phase 0→6 rerun stopped at Phase 1.

Phase 2–6 were not called. They were marked:

`skipped_due_to_prior_block`

Skip reason:

`ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING`

This preserves the H1B6.R1 harness rule: first canonical block stops later public phases.

## CVL / Phase 0 Calibration

Phase 0 remained cognitive-only:

- runtime executed: `false`
- task created: `false`
- task_run created: `false`
- operation created: `false`
- operational artifacts created: `false`

Prediction:

- `predicted_frontier = ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP`
- `predicted_component = artifact_worker_terminalization_guard`
- `predicted_reason_code = ARTIFACT_RUNTIME_STALLED_AFTER_ARTIFACT_CREATION_STARTED`
- decision: `NO_GO_EXPECTED_BLOCK`
- confidence: `0.86`

The runtime outcome was terminalized as an artifact creation exception rather than a silent stall, so the calibration is close in component/frontier class and no longer drifts to `TRUTH_READINESS`.

## Public Clean Rerun

Observation report:

`reports/runtime_consolidation/firetest5_h1c0_r2_7_clean_phase0_to_6_rerun_observation.json`

Raw capture:

`reports/firetest5/firetest5_h1c0_r2_7_clean_phase0_to_6_20260816_044729`

Phase 1:

- `client_response_status = accepted_running`
- `client_response_status_code = 200`
- `client_response_time_ms = 6514`
- `task_run_id = task_run_4abdb0e40a0a41ffb57b8b7861195687`
- `operation_id = op_6d114217d6f349b89071ce08d984036c`
- `run_status_from_run_json = blocked`
- `run_status_from_index = blocked`
- `result_json_exists = true`
- `result_endpoint_status_code = 200`
- `result_status = blocked`
- `result_source = phase_semantic_completion_policy`
- `result_reason_code = ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING`
- `finished_at = 2026-08-16T07:48:06.123311+00:00`
- `terminal_event_count = 1`
- `artifact_creation_started_count = 1`
- `artifact_failed_count = 1`

Artifact outcome:

- `phase1_discovery.md = blocked`
- `music_inventory.csv = not_reached`
- `evidence_phase1.zip = not_reached`

The metadata/sufficiency path from R2.6 was preserved in tests, but the public run still does not reach it.

## Queue / Storage Health

Before public rerun:

- `active_runs = 0`
- `queued_runs = 0`
- `stale_runs = 0`
- `pending_approvals = 0`
- `large_run_count = 0`
- `missing_index_count = 0`

After public rerun:

- `active_runs = 0`
- `queued_runs = 0`
- `stale_runs = 0`
- `pending_approvals = 0`
- `large_run_count = 0`
- `missing_index_count = 0`

Payload sizes:

- `run_json_bytes = 74219`
- `result_json_bytes = 51281`
- `events_json_bytes = 30827`

No manual cleanup was required for queue health after the final rerun.

## Tests

Focused guard/CVL:

`8 passed in 14.37s`

Runtime regressions:

`43 passed in 128.16s`

R2.6 / R2.5 service-equivalent regressions:

`40 passed, 1 skipped in 14.66s`

Integrated runtime/semantic regressions:

`93 passed in 72.02s`

Post exception-specific patch focused regressions:

`18 passed in 101.86s`

CVL/readiness regressions:

`20 passed in 0.54s`

Some prompt-listed test files are not present in the current checkout. Equivalent existing suites were run and passed.

## Py Compile

`python -m compileall -q src tests/unit/test_accepted_running_artifact_worker_terminalization_guard.py tests/unit/test_cvl_artifact_worker_terminalization_frontier.py`

Result: PASS.

## Anti-Hardcode

Production audit found no new decision branch based on:

- FireTest-specific success;
- Pinhoabacaxi;
- local paths;
- exact task_run id;
- exact operation id;
- exact artifact path;
- artifact name as success authority;
- extension as truth.

Only existing structural CVL names such as `FireTestProfile` / `FireTestLaboratoryService` remain.

## Why No False Success

The patch terminalizes failures and stalls; it does not promote them.

The public rerun ended with:

- `result.status = blocked`
- `completion.safe_to_report_success = false`
- `truth.safe_to_report_success = false`
- Phase 2–6 skipped

`accepted_running` remained non-success, and `result.json` existence did not imply completion.

## Why R2.6 Metadata Was Preserved

The metadata capability/sufficiency work remains service-equivalent and regression-tested. R2.7 did not change metadata probing, schema sufficiency, root binding, entity selection, relationship truth, or renderer observation.

Public metadata proof is still blocked before `music_inventory.csv` is reached.

## Current Frontier

The current public blocker is no longer orphaned accepted-running terminality.

New frontier:

`ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING`

The observed exception occurs after `artifact_creation_started` for the first Phase 1 artifact, before `music_inventory.csv` and before metadata sufficiency public proof.

The next repair should diagnose the artifact creation exception path, especially the large governed payload/ref hydration or JSON parsing behavior observed after artifact start. It should remain narrow and must not reopen metadata unless the artifact exception proves metadata-related.

## Next Recommendation

Proceed with a narrow repair slice:

`H1C0.R2.8 — Artifact Creation Exception After Accepted Running / Payload Ref Hydration Boundary`

Target:

- artifact runtime exception after `artifact_creation_started`;
- preserve guard terminality;
- keep `/result=200`;
- keep Phase 2–6 skipped on Phase 1 block;
- do not re-open metadata/root binding/entity selection unless the exception trace proves that boundary is the cause.

FireTest 5 remains `NOT_READY`.
