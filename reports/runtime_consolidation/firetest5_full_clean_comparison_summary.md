# FireTest 5 Full Clean Comparison

- generated_at: `2026-08-13T06:28:48.901913+00:00`
- verdict: `FIRETEST5_FULL_CLEAN_COMPARISON_COMPLETED_WITH_SEMANTIC_CONTRACT_FINDINGS`
- session_id: `None`
- task_run_id: `task_run_0ec7859b6d674b17a759b932cff4493a`

## Objective

Run FireTest 5 from a clean/hygienized public path for comparison, without code changes during execution, without forcing later phases, and without declaring success beyond what Runtime, Validation, Completion, and Speaker Truth actually recorded.

## Clean Precheck

- API health: `ok`
- queue before: `active_runs=0`, `queued_runs=0`, `pending_approvals=0`
- storage projection before/latest: no missing indexes and no run.json above 1 MB threshold
- backend port: `9088`

## Phase 0 / CVL

- decision: `NO_GO_EXPECTED_BLOCK`
- confidence: `0.78`
- predicted_frontier: `PUBLIC_CHAT_RESPONSE_BOUNDARY`
- predicted_component: `PublicRuntimeResponsePolicy`
- predicted_reason_code: `PUBLIC_CHAT_RESPONSE_BOUNDARY`

Phase 0 predicted a public boundary block, but Phase 1 completed. Calibration therefore recorded a mismatch/false positive. This is useful calibration debt, not a runtime failure.

## Public Chat Response

- HTTP status: `200`
- client_response_status: `accepted_running`
- client_response_time_ms: `6197`
- structured task_run_id field: `None`
- result_ref_id: `task_run_0ec7859b6d674b17a759b932cff4493a`
- message contained task_run_id: `True`

Finding: `accepted_running` was returned quickly, but the structured `task_run_id` field was null while `result_ref_id` and message contained the run id. This is public response contract drift and should be repaired without changing FireTest semantics.

## Runtime Result

- run.status: `completed`
- result.status: `completed`
- finished_at: `2026-08-13T06:23:36.482060+00:00`
- event_count: `24`
- terminal_event_count: `1`
- run.json size: `91809` bytes
- run_index.json size: `862` bytes
- result.json size: `165038` bytes

## ProjectAnalysis

- status: `partial`
- reason_code: `PROJECT_ANALYSIS_COMPLETED`
- safe_to_continue: `True`
- files_discovered: `76`
- files_selected: `12`
- files_read: `12`
- files_partial_read: `0`
- files_skipped: `0`
- bytes_read: `34564`
- partial_readiness: `{"safe_to_continue_to_artifact_runtime": true, "confidence": 0.72, "missing_context": [], "reason_codes": ["PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE"]}`

ProjectAnalysis no longer blocked on single-file read. It produced partial context and allowed artifact runtime to continue.

## Artifacts

| Logical path | Status | Validation | Size bytes | Artifact id |
|---|---:|---:|---:|---|
| `reports/firetest5/phase1_discovery.md` | `ready` | `validated` | 9556 | `artifact_b15303219a3a49a6b6fed57888bd058f` |
| `reports/firetest5/project_inventory.md` | `ready` | `validated` | 9557 | `artifact_3ac2aae1ae784351913adabfbf3e3c76` |
| `reports/firetest5/music_inventory.csv` | `ready` | `validated` | 8947 | `artifact_9af616866a4043a4b68a29ab363785a3` |
| `reports/firetest5/evidence_phase1.zip` | `ready` | `validated` | 209511 | `artifact_7cbadcaa611a46399945b2cd143ada62` |

Event counts:

- artifact_creation_started: `4`
- artifact_created: `4`
- artifact_late_rejected: `0`
- terminal events: `['run_completed']`

## Music Inventory Shape

- path: `C:\Dev\AIpinho\data\artifacts\universal\artifact_9af616866a4043a4b68a29ab363785a3_reports__firetest5__music_inventory.csv`
- rows: `14`
- columns: `['severity', 'title', 'summary']`
- project-like references in rows: `8`

Finding: `music_inventory.csv` was created and validated by the current contract, but its shape is `severity,title,summary`; it is not a rich per-track inventory. Some rows reference project files because the artifact content is a readonly analysis findings CSV, not a corpus inventory table. This is a semantic contract/materialization gap, not a ProjectAnalysis or lifecycle failure.

## Validation / Completion / Truth

- summary.status: `COMPLETED`
- validation.status: `passed`
- result.status: `completed`
- result.validation.status: `passed`
- result.completion.status: `completed`
- Speaker Truth status: `allowed`
- Speaker Truth safe_to_report_success: `True`

Runtime Truth allowed success for the currently declared readonly artifact contract. The semantic finding above means the next comparison should tighten artifact contract expectations before treating this as FireTest-ready behavior.

## Observational / Relationship Cognition

- observational_cognition.status: `not_available`
- media_metadata_capability.status: `not_configured`
- relationship_cognition.status: `not_available`
- relationship candidate_count: `0`
- relationship validation_status: `blocked`

The H1B5 relationship stack was not exercised by this public run. It remained `not_available` because the artifact contract path did not bind relationship candidates.

## Endpoint Timings Final

| Endpoint | ok | HTTP | elapsed_ms | bytes | error |
|---|---:|---:|---:|---:|---|
| `summary` | `True` | 200 | 39 | 7674 | `None` |
| `truth` | `True` | 200 | 5392 | 2805 | `None` |
| `events` | `True` | 200 | 16 | 64203 | `None` |
| `artifacts` | `True` | 200 | 58 | 11331 | `None` |
| `result` | `True` | 200 | 49 | 116775 | `None` |

During polling there were transient active-run endpoint findings:

| Poll | Endpoint | elapsed_ms | error |
|---:|---|---:|---|
| 0 | `summary` | 20008 | `TimeoutError('timed out')` |
| 0 | `result` | 6 | `<HTTPError 404: 'Not Found'>` |
| 1 | `result` | 253 | `<HTTPError 404: 'Not Found'>` |
| 2 | `result` | 7 | `<HTTPError 404: 'Not Found'>` |
| 3 | `result` | 297 | `<HTTPError 404: 'Not Found'>` |
| 4 | `result` | 11 | `<HTTPError 404: 'Not Found'>` |
| 5 | `result` | 33 | `<HTTPError 404: 'Not Found'>` |

## Phase0 vs Phase1 Calibration

- status: `mismatch`
- confidence_error: `0.5477`
- overall_accuracy_score: `0.2323`
- false_positive: `True`
- divergence: `Prediction diverged from actual runtime boundary. Predicted PUBLIC_CHAT_RESPONSE_BOUNDARY/PublicRuntimeResponsePolicy/PUBLIC_CHAT_RESPONSE_BOUNDARY; actual None/None/None.`

## Queue / Storage After

- queue status: `ok`
- active_count: `0`
- pending_count: `0`
- requires_decision_count: `0`
- storage status: `ok`
- missing_index_count: `0`
- large_run_count: `0`

## Comparison Verdict

This clean comparison shows major recovery versus the previous blockers:

- H1B6 public boundary worked: no 360s synchronous wait.
- H1B5.R1 ProjectAnalysis budget cooperation worked: partial context continued safely.
- Artifact lifecycle worked: 4 starts, 4 created, 0 late rejects, 1 terminal event.
- Queue and storage projections stayed healthy.

Remaining findings:

- `accepted_running.task_run_id` structured field is null despite `result_ref_id` carrying the run id.
- Phase 0 overpredicted a public boundary block and needs recalibration after H1B6/R1.
- `music_inventory.csv` is structurally a findings CSV, not a true music inventory table.
- `observational_cognition` and `relationship_cognition` remained `not_available`; H1B5 relationship flow was not exercised publicly.
- One active-run summary poll timed out, and final truth took 5392 ms.

Recommended next step: repair the public response `task_run_id` projection and tighten relationship/music inventory artifact contracts so a future ?complete? FireTest cannot pass with a shallow artifact shape.
