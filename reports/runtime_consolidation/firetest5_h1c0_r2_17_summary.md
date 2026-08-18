# H1C0.R2.17 — CSV Cell Value Extraction / Indexed Lookup Cost Boundary

## Verdict

FIRETEST5_H1C0_R2_17_CSV_CELL_VALUE_INDEXED_LOOKUP_READY

FireTest 5 = NOT_READY

## Repository

- Local repository bootstrap completed from R2.16 baseline.
- `origin/main` published: `8c8914b79c9faf28c81d91138b3672581b453563`.
- GitHub auth verified as `sasandralean-prog` through official GitHub CLI device flow.
- No force push.
- Branch: `h1c0-r2.17-csv-cell-extraction`.

## Root Cause

Root cause status: proven.

The expensive cell operation was not `csv.writer` serialization. The hot path repeatedly resolved `metadata_status`, `metadata_source`, and `probe_status` by scanning the full `attribute_observations` list per entity/cell. This created an O(rows x metadata columns x observations) lookup boundary.

## Timing Semantics

R2.16 Diagnostic A and Validation B used different timer coverage semantics. R2.17 separates:

- `cell_value_lookup_elapsed_ms`: value source identification and governed lookup;
- `cell_normalization_elapsed_ms`: normalization/render/spill-to-ref;
- `csv_cell_serialization_elapsed_ms`: legacy-compatible render/normalization counter, not csv.writer cost.

## Patch

R2.17 introduced a generic per-render immutable lookup context:

- media metadata observations grouped by entity;
- observed attribute values by `(entity_id, canonical_key)`;
- entity field value projection for direct lookup;
- precomputed relationship render values;
- cached canonicalization for schema/attribute keys;
- bounded aggregate metrics and per-column cost profile.

The index is an access projection only. It does not create truth, evidence, validation, completion, or SpeakerTruth.

## Public Validation

Diagnostic run:

- task_run_id: `task_run_033998b4118145af9f2ea1d7ad014b6e`
- result.reason_code: `MEDIA_INVENTORY_IDENTITY_COVERAGE_INSUFFICIENT`
- last_stage: `after_registry_create_before_event`

Clean validation run:

- task_run_id: `task_run_72568219bfbf4ab8ac11f048e44dd4b8`
- result.status: `blocked`
- result.reason_code: `MEDIA_INVENTORY_IDENTITY_COVERAGE_INSUFFICIENT`
- /result: `200`
- finished_at: `2026-08-18T11:11:12.701560+00:00`
- terminal_event_count: `1`
- SpeakerTruth.safe_to_report_success: `False`
- music_inventory_reached: `True`
- metadata_coverage_reached: `True`
- inventory_sufficiency_reached: `True`
- evidence_phase1_reached: `True`
- Phase 2-6: skipped_due_to_prior_block

## Cost Evidence

R2.16 Validation B:

- csv_stream_elapsed_ms: 258030
- csv_cell_render_elapsed_ms: 239110
- csv_cell_serialization_elapsed_ms: 16

R2.17 clean validation:

- csv_stream_elapsed_ms: 92063
- csv_cell_render_elapsed_ms: 88493
- csv_cell_serialization_elapsed_ms: 14
- cell_value_lookup_elapsed_ms: 17165
- cell_fallback_scan_count: 0
- index_build_elapsed_ms: 61

Generic scale validation largest fixture:

```json
{"entities": 2500, "observations": 62500, "lookup_calls": 7500, "old_scan_items_estimate": 468750000, "old_elapsed_ms": 35354.591, "index_build_elapsed_ms": 15.0, "index_build_wall_ms": 23.126, "indexed_lookup_elapsed_ms": 20.508, "indexed_total_elapsed_ms": 43.635, "speedup_x_including_build": 810.244, "index_entry_count": 62513, "index_bytes_estimate": 170}
```

## Payload Ref Carry-In

Artifact persistence was reached publicly. Payload ref physical validation observed:

- physical_ref_count: 3
- physical_total_bytes: 268204736
- unique_hash_count: 3
- duplicate_hash_groups: 0

## Endpoint Health

Clean validation endpoints were responsive: {"summary": {"status_code": 200, "elapsed_ms": 5757, "ok": true}, "events": {"status_code": 200, "elapsed_ms": 119, "ok": true}, "result": {"status_code": 200, "elapsed_ms": 35, "ok": true}, "truth": {"status_code": 200, "elapsed_ms": 596, "ok": true}, "artifacts": {"status_code": 200, "elapsed_ms": 76, "ok": true}, "session": {"status_code": 200, "elapsed_ms": 59, "ok": true}, "queue_hygiene": {"status_code": 200, "elapsed_ms": 34, "ok": true}, "queue_runtime": {"status_code": 200, "elapsed_ms": 66, "ok": true}}

## Tests

- py_compile: PASS for `readonly_analysis_artifact_runtime_service.py` and `h1c0_r2_17_collect_public_rerun.py`.
- focused tests: 12 passed.
- regression set: 65 passed, 1 skipped.
- anti-hardcode: PASS for changed production logic; no branch by FireTest, Pinhoabacaxi, artifact path/name, extension, fixed row counts, task_run_id, operation_id, or local path.

## New Frontier

MEDIA_INVENTORY_IDENTITY_COVERAGE_INSUFFICIENT

The CSV cell lookup boundary is ready. FireTest 5 remains NOT_READY because semantic identity coverage is insufficient.
