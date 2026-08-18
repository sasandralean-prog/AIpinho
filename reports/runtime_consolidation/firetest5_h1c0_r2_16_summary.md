# H1C0.R2.16 — CSV Row Cardinality, Streaming Determinism & Cost-Bounded Rendering

## Verdict

FIRETEST5_H1C0_R2_16_CSV_CARDINALITY_STREAMING_DETERMINISM_BLOCKED_WITH_CORE_FIX_VALIDATED

FireTest 5 = NOT_READY

## Objective

Investigate the CSV streaming boundary after R2.15, distinguish cardinality drift from deterministic row-domain differences, preserve terminality, and avoid turning artifact existence or result existence into semantic success.

## Root Cause Status

- CSV stall misclassification: proven and fixed. Progressing CSV work now terminalizes as MUSIC_INVENTORY_CSV_STREAMING_BUDGET_EXCEEDED instead of a generic no-progress stall.
- Cardinality ambiguity: proven and fixed. The public chain is source_input_entity_count=2286, selected_entity_count=2272, projected_entity_count=2272, row_model_accepted_count=2230, row_model_skipped_count=42, csv_rows_expected_at_stream_start=2230.
- CSV cost frontier: proven but still open as a new frontier. Full cell processing accumulated 239110 ms in validation run B, while cell serialization itself accumulated 16 ms.
- Payload-ref subtree amplification: fixed in production and unit validated, but not public-reached in R2.16 because both public runs blocked before artifact persist.

## Public Reruns

Diagnostic A:
- task_run_id: task_run_f5abad70e03c4955b15c0ee5d9523503
- result: blocked / MUSIC_INVENTORY_CSV_STREAMING_BUDGET_EXCEEDED
- terminal_event_count: 1
- last_completed_stage: before_csv_cell_render

Validation B:
- task_run_id: task_run_0b0cbc1d3a74411a9fd47b751039e45c
- result: blocked / MUSIC_INVENTORY_CSV_STREAMING_BUDGET_EXCEEDED
- /result: 200
- finished_at: 2026-08-18T03:20:08.861963+00:00
- terminal_event_count: 1
- SpeakerTruth.safe_to_report_success: False
- last_completed_stage: before_csv_cell_render

## Determinism

A/B digests match for input entity set, projected entity set, row model, render order, and column schema. Rows/cells written differ only because the same budget-exceeded terminalization fired at different progress depths.

## Cost Model

Validation B:
- csv_stream_elapsed_ms: 258030
- csv_row_render_elapsed_ms: 238141
- csv_cell_render_elapsed_ms: 239110
- csv_cell_serialization_elapsed_ms: 16
- rows_per_second: 6.675
- cells_per_second: 166.878

Interpretation: serialization is not the dominant cost. The next frontier is the full cell value extraction/render path, likely lookup/provenance-aware extraction rather than csv.writer serialization.

## Changed Files

- src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- src/aipinho/services/artifacts/universal_artifact_registry_service.py
- reports/runtime_consolidation/h1c0_r2_16_collect_public_rerun.py
- tests/unit/test_csv_cardinality_render_metrics.py
- tests/unit/test_artifact_persist_payload_ref_boundary.py
- tests/unit/test_music_inventory_artifact_worker_stall_terminality.py
- tests/unit/test_music_inventory_observational_binding_public.py

## Tests

- py_compile: PASS
- focused/wide regression: 53 passed in 79.83s
- initial attempted regression included a historical missing file name and collected 0 tests; rerun used existing equivalent files and passed.

## Anti-Hardcode

PASS on changed production files. No production decision branch was introduced for FireTest, Pinhoabacaxi, artifact path/name, extension, task id, operation id, or observed row counts.

## Endpoint Health

Validation B endpoints remained responsive:
- summary: {'status_code': 200, 'elapsed_ms': 604, 'ok': True}
- events: {'status_code': 200, 'elapsed_ms': 89, 'ok': True}
- result: {'status_code': 200, 'elapsed_ms': 34, 'ok': True}
- truth: {'status_code': 200, 'elapsed_ms': 18, 'ok': True}
- artifacts: {'status_code': 200, 'elapsed_ms': 6615, 'ok': True}
- queue_runtime: {'status_code': 200, 'elapsed_ms': 815, 'ok': True}

## Semantic State

- metadata_coverage_reached: False
- inventory_sufficiency_reached: False
- evidence_phase1_reached: False
- Phase 2-6: skipped_due_to_prior_block; api_called=false.

## No False Success

The run remains blocked. result.json exists only as terminal governance evidence, not as completion. SpeakerTruth.safe_to_report_success=false. CSV progress is not treated as inventory semantic success.

## Divergences

The compact phase1 checkpoint projection is intentionally sparse; the events endpoint carries bounded aggregate metrics and is the source used by R2.16 reports. Observation concrete data wins over summary narration.

## Next Frontier

H1C0.R2.17 should focus on generic CSV cell value extraction/indexed lookup cost under provenance/truth constraints, not on artifact-specific CSV formatting or music-specific rules.
