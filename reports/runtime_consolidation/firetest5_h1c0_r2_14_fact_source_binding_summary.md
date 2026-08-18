# H1C0.R2.14 Fact Source Binding Summary

Verdict: `FIRETEST5_H1C0_R2_14_GOVERNED_FACT_SOURCE_BINDING_BLOCKED_WITH_CORE_FIX_VALIDATED`

FireTest 5: `NOT_READY`

## Objective

R2.14 targeted the frontier exposed by R2.13: `before_fact_source_binding -> fact source binding -> after_fact_source_binding`, plus canonical terminal reason consistency. The goal was not to make the FireTest fixture pass; it was to make fact source binding observable, bounded and provenance-aware without creating fixture-specific production behavior.

## Before State

R2.13 public run `task_run_a85129892a9d4ac29d3bfe0225de9883` terminalized as blocked with observed reason `PERCEPTION_FACT_SOURCE_BINDING_STALLED`. The result endpoint returned 200 and terminality was healthy, but top-level `TaskRunResult.reason_code` was null while validation/completion/events carried the blocking reason.

## Diagnosis

Root cause status: `proven`.

`ContractDrivenPerceptionService.compile()` still had a monolithic source-binding region. Between `before_fact_source_binding` and `after_fact_source_binding`, it performed attribute observation projection, evidence set materialization, semantic coverage and coverage report generation without internal public checkpoints. This made the R2.13 blocker accurate but too coarse.

## Changed Files

- `src/aipinho/schemas/runtime/task_run_result.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/task_run_result_service.py`
- `src/aipinho/services/runtime/phase_semantic_result_finalizer.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/runtime/canonical_operation_state_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `config/runtime/task_run_event_policy.yaml`

## Patch

Fact source binding now emits bounded generic subcheckpoints:

- source index build
- attribute observation projection
- evidence ref resolution
- evidence set materialization
- source provenance binding
- source binding bound check

The compiler path uses indexed source-binding inputs and progress callbacks. It does not execute observers, scan the filesystem, render CSV, decide Completion, decide SpeakerTruth or promote candidates to Truth.

Terminal result coherence was strengthened by adding canonical top-level `TaskRunResult.reason_code` and making result/session/summary projections prefer it. The artifact worker guard now measures silence since the last checkpoint, not total artifact age, so active work is not falsely terminalized.

## Public Clean Rerun

Task run: `task_run_b8b2925ff06b4682938f28f3ec7af356`

Operation: `op_8f0b098f7a554eedb7be6523404e239a`

Observed result:

- `result.status = blocked`
- `result.reason_code = MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED`
- `result_top_level_reason_code = MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED`
- `/result = 200`
- `finished_at = 2026-08-17T17:59:47.481218-03:00`
- `terminal_event_count = 1`
- `terminal_event_types = [run_blocked]`
- `SpeakerTruth.safe_to_report_success = false`

Artifact progression:

- `artifact_creation_started_count = 3`
- `artifact_created_count = 2`
- `artifact_failed_count = 1`
- `music_inventory_reached = true`
- `evidence_phase1_reached = false`

Source binding progression:

- `before_fact_source_binding = true`
- `after_fact_source_binding = true`
- `after_fact_projection = true`
- `before_payload_assembly = true`
- `after_payload_assembly = true`
- `metadata_coverage_reached = true`
- `inventory_sufficiency_reached = true`
- final `last_completed_stage = before_artifact_persist`

Endpoint health:

- `summary = 200 / 31 ms`
- `events = 200 / 42 ms`
- `result = 200 / 15 ms`
- `truth = 200 / 13 ms`
- `artifacts = 200 / 21 ms`
- `session = 200 / 32 ms`
- `queue_hygiene = 200 / 8 ms`
- `queue_runtime = 200 / 21 ms`

Phase 2-6 were all `skipped_due_to_prior_block` with `api_called=false`.

## Metrics

Final public projection retained:

- `estimated_payload_bytes = 17194840`
- `materialized_payload_bytes = 17194840`
- `payload_ref_count = 0`

This does not prove the full persist root cause alone, but it is strong evidence that the next frontier is artifact persist payload-ref/materialization, not source binding.

## Tests

Observed test results:

- New/source-binding tests: `7 passed`
- Observation-binding followup: `8 passed`
- Terminality followup: `27 passed`
- Result/finalization projection followup: `29 passed`
- ProjectAnalysis event-policy regression after fix: `3 passed`
- Final focused regression: `104 passed`

`py_compile` passed for the changed production files and the R2.14 collector.

## Anti-Hardcode

Anti-hardcode audit passed. Matches in production were structural identifiers such as `task_run_id`, `artifact_attempt_id`, and the pre-existing structural `FireTestProfile` CVL profile. No production decision branch was added for Pinhoabacaxi, FireTest, artifact logical path, filename, extension, row count, task id or operation id.

## Why This Is Not False Success

The run stayed blocked. `result.json` exists, but that was not treated as completion. Speaker Truth remained false. `music_inventory.csv` was reached, but artifact existence and artifact start were not treated as inventory success. Metadata coverage and sufficiency were reached, but the run blocked before artifact persist completed; no later phase was executed.

## Remaining Frontier

New P0: `MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED`.

The next wave should focus on artifact persist payload-ref/materialization boundary, atomic persist, large artifact payload handling and sharded manifest behavior. A reasonable name is:

`H1C0.R2.15 -- Artifact Persist Payload Ref Boundary & Large Materialization Control`
