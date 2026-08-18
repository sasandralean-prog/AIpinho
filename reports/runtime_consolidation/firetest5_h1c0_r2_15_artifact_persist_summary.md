# H1C0.R2.15 Artifact Persist Payload Ref Boundary & Large Materialization Control

## Verdict

FIRETEST5_H1C0_R2_15_ARTIFACT_PERSIST_PAYLOAD_REF_BOUNDARY_BLOCKED_WITH_CORE_FIX_VALIDATED

FireTest 5: NOT_READY

## Root Cause Status

- Artifact persist payload/ref boundary: proven and core fix validated in diagnostic rerun.
- Run-to-run divergence: not_yet_proven.
- Final public frontier: MUSIC_INVENTORY_CSV_STREAMING_STALLED.

## What Changed

- Added bounded artifact persist checkpoints through payload classification, serialization, payload-ref decision, content write, manifest persist, registry index update, and commit.
- Added generic payload-ref spill for large manifest metadata/provenance payloads.
- Added atomic content write and cleanup on manifest/index failure.
- Preserved sharded registry and legacy registry skip behavior.
- Prevented post-commit checkpoint from retroactively converting completed persist into artifact render timeout.
- Mapped known render-stage timeout to stage-specific reason instead of generic ARTIFACT_RENDER_TIMEOUT.
- Fixed R2.15 report collector to separate persist by logical path and merge bounded metrics from music inventory checkpoints.

## Public Evidence

Diagnostic rerun:

- task_run_id: task_run_2494e9d32e2548e1896e074823b715c9
- music_inventory last stage: after_artifact_persist
- after_artifact_persist reached: True
- reason: ARTIFACT_RENDER_TIMEOUT

Final rerun:

- task_run_id: task_run_f23704fcec1f4874bdef0c2cfb972c9e
- result.status: blocked
- result.reason_code: MUSIC_INVENTORY_CSV_STREAMING_STALLED
- /result: 200
- finished_at: 2026-08-18T02:15:25.857691+00:00
- terminal_event_count: 1
- SpeakerTruth.safe_to_report_success: False
- queue_runtime elapsed_ms: 13
- music_inventory reached: True
- music_inventory after_artifact_persist reached in final: False
- metadata_coverage_reached: False
- inventory_sufficiency_reached: False
- evidence_phase1_reached: False
- Phase 2-6: skipped_due_to_prior_block

## Payload / Metrics

- Final bounded metrics merged from music checkpoints: 54 scalar fields.
- Final music persist checkpoints: 0.
- Persist-by-logical-path confirms only earlier artifacts reached persist in the final rerun.

## Divergence

The diagnostic run reached music inventory artifact persist. The final run blocked earlier at before_csv_cell_render. This divergence is observed but not explained. No patch in R2.15 claims to solve cache, scheduler, GC, ordering, or CSV cell render cost variability.

## Tests

- py_compile: PASS for changed production/report/test files.
- Focused/regression pytest: 40 passed.
- Anti-hardcode: PASS for fixture/path/artifact/ext/local ids; matches were benign generic task_run/artifact_attempt identifier fields.

## Why No False Success

The final result is blocked, SpeakerTruth is false, Phase 2-6 were skipped, metadata coverage and inventory sufficiency were not reached in the final public run, and no CSV existence or result existence was treated as completion.

## Next Frontier

CSV streaming/cell rendering determinism and cost model. The next wave should explain why equivalent public runs can either reach persist or block at before_csv_cell_render under the same artifact budget.
