# H1C0.R2.5 - Semantic Completion Finalization Handoff Before Lifecycle Repair

## Verdict

`FIRETEST5_H1C0_R2_5_SEMANTIC_COMPLETION_FINALIZATION_HANDOFF_READY`

FireTest 5 is still `NOT_READY`. Phase 1 remains blocked, but it now blocks for the semantic reason from `PhaseSemanticCompletionPolicy`, not because `TaskRunStore` repaired the result as `TASKRUN_LIFECYCLE_TIMEOUT`.

## Objective

Put the semantic judge before the lifecycle repair fallback: artifact runtime state -> PhaseSemanticCompletionPolicy -> Validation/Completion/Speaker Truth -> result persistence, with TaskRunStore repair only as fallback.

## Before State

R2.4 produced artifacts and evidence, but the public terminal result was repaired by `TaskRunStore` with `TASKRUN_LIFECYCLE_TIMEOUT` and `terminal_result_missing_repaired`.

## Changed Files

- `src/aipinho/services/runtime/phase_semantic_result_finalizer.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/phase_semantic_completion_policy.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/schemas/runtime/task_run_result.py`
- `tests/unit/test_semantic_completion_finalization_handoff.py`
- `tests/unit/test_task_run_store_repair_does_not_preempt_semantic_completion.py`
- `tests/unit/test_cvl_semantic_completion_finalization_handoff_frontier.py`
- `tests/unit/test_result_finalization_after_partial_artifact_binding.py`

## Exact Handoff Fixed

- Added `PhaseSemanticResultFinalizer` to build a terminal `TaskRunResult` from already-governed artifact semantic state.
- `TaskRunStore.ensure_terminal_result()` now attempts semantic finalization before conservative repair.
- `TaskRunStore.terminalize_if_runtime_budget_exceeded()` suppresses timeout repair when semantic artifact state is sufficient.
- Real timeout repair remains active when there is no semantic artifact state.
- `TaskRunResult` now exposes `source` and `finished_at`.

## Semantic Policy Proof

- policy called: `True`
- decision persisted: `True`
- decision status: `blocked`
- decision reason: `MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT`
- result.source: `phase_semantic_completion_policy`
- store repair suppressed: `True`

## Public Phase 1 Rerun

- task_run_id: `task_run_b59d89c948fb4a47a1c7e150a02808a3`
- client status: `accepted_running`
- result.status: `blocked`
- result.source: `phase_semantic_completion_policy`
- result.reason_code: `MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT`
- finished_at: `2026-08-15T05:36:52.375909+00:00`
- terminal_event_count: `1`
- terminal_event_types: `['run_blocked']`

## Music Inventory

- expected_rows: `1051`
- selected_rows: `100`
- bound_rows: `100`
- partial_rows: `100`
- evidence_ref_count: `100`
- row_evidence_coverage: `satisfied`
- semantic_contract_status: `partial`
- safe_to_use: `False`

## Evidence Phase 1

- status: `ready`
- semantic_contract_status: `satisfied`
- safe_to_use: `True`

## Validation / Completion / Speaker Truth

- validation.status: `blocked`
- validation.reason_code: `MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT`
- completion.status: `blocked`
- completion.safe_to_report_success: `False`
- truth.status: `blocked`
- truth.safe_to_report_success: `False`

No false success was emitted. Phase 2 through Phase 6 were `skipped_due_to_prior_block` and were not called canonically.

## Endpoint Timings

- `summary`: status 200, 1775 ms
- `result`: status 200, 525 ms
- `truth`: status 200, 859 ms
- `artifacts`: status 200, 1433 ms
- `events`: status 200, 7672 ms

## Queue / Storage

- active_count: `0`
- large_run_count: `0`
- missing_index_count: `0`
- run.json bytes: `159545`
- result.json bytes: `28114`
- events.json bytes: `34722`

## Tests

- Focused R2.5: `6 passed in 0.91s`
- Affected runtime slice: `26 passed in 59.03s`
- Integrated existing regression: `95 passed in 93.01s`
- `py_compile`: `PASS`
- anti-hardcode: `PASS`; no project/path/task-run/artifact-name success branch in changed production files.

## Remaining Gaps

Phase 1 still blocks because the default phase contract rejects partial inventory as final success. Column alias noise remains P1, but it no longer becomes lifecycle timeout.

## Next Recommendation

Decide the actual Phase 1 semantic policy: either accept partial evidence-bound discovery as `completed_with_limitations`, or keep Phase 1 blocked and move to the next evidence/contract repair. FireTest 5 remains NOT_READY until Phase 1 can complete or later phases are canonically skipped by an accepted contract.

## Why No False Success

`music_inventory.csv` remains `safe_to_use=false`, validation/completion are blocked, Speaker Truth is false, and Phase 2 was not run.
