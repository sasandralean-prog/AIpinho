# H1C0.R2.12 — Governed Perception Payload Compilation Boundaries & Bounded Materialization

## Verdict

`FIRETEST5_H1C0_R2_12_GOVERNED_PERCEPTION_PAYLOAD_COMPILATION_READY`

FireTest 5: `NOT_READY`.

## Objective

Make `ContractDrivenPerceptionService.compile()` observable, governed, bounded and generic. The wave did not make a FireTest-specific compiler and did not turn artifact existence into semantic success.

## Before State

R2.11 public proof stopped at `before_perception_payload_compile` with `MUSIC_INVENTORY_PERCEPTION_PAYLOAD_COMPILE_STALLED`.

## Root Cause

`root_cause_status=proven`: the compile boundary mixed perception compilation with observer execution and relationship detection. That made the boundary too large and made stalls appear as a generic artifact-level stall instead of an internal perception stage.

## Patch

Changed files:

- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `tests/unit/test_contract_driven_perception_compile_stage_trace.py`
- `tests/unit/test_cvl_perception_payload_compile_frontier.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_music_inventory_metadata_coverage.py`
- `reports/runtime_consolidation/h1c0_r2_12_collect_public_rerun.py`

Implemented:

- internal bounded stage trace for compile;
- `compile_only` policy for public artifact runtime;
- deferred observer execution and relationship detection inside compile-only;
- payload metrics and payload/budget block reasons;
- generic stage-specific reason propagation;
- CVL prediction for perception payload compile boundary;
- canonical checkpoint metadata protection;
- no checkpoint emitted after terminal event.

## Public Clean Rerun

- `task_run_id=task_run_343bb3198f2a4a978611eb7b0fd2e242`
- `result.status=blocked`
- `result.reason_code=PERCEPTION_FACT_PROJECTION_STALLED`
- `/result=200`
- `finished_at=2026-08-17T14:26:18.409430+00:00`
- `terminal_event_count=1`
- `SpeakerTruth.safe_to_report_success=False`
- `music_inventory_reached=True`
- `last_completed_internal_compile_stage=before_fact_projection`
- `after_perception_payload_compile_reached=False`
- `metadata_coverage_reached=False`
- `inventory_sufficiency_reached=False`
- `evidence_phase1_reached=False`

Phase 2–6: `skipped_due_to_prior_block`, `api_called=false`.

## Endpoint Health

- summary: `200` / `502ms`
- events: `200` / `52ms`
- result: `200` / `15ms`
- truth: `200` / `61ms`
- artifacts: `200` / `31ms`
- queue_hygiene: `200` / `15ms`
- queue_runtime: `200` / `408ms`

No backend restart was needed after terminal result.

## Tests

- Focused: `21 passed in 33.06s`
- Wide regression: `116 passed in 93.77s`
- `py_compile`: PASS
- anti-hardcode: PASS; only pre-existing CVL structural names `FireTestProfile`, `FireTestSuite`, `FireTestLaboratoryService` matched in production files.

## Why No Bypass

The public runtime still blocks. `result.json` exists, but it is not success. The compiler does not observe filesystem, does not read media, does not render CSV, does not decide Completion, and does not decide Speaker Truth.

## Remaining Frontier

The next public frontier is now generic and narrower: `PERCEPTION_FACT_PROJECTION_STALLED`. The runtime reached `before_fact_projection`, then terminalized safely before `after_perception_payload_compile`; metadata coverage, inventory sufficiency and evidence package were not reached.
