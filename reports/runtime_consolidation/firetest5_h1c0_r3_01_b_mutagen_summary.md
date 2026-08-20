# FireTest 5 H1C0.R3.01.B Mutagen-Present Diagnostic

Verdict: `FIRETEST5_R3_01_B_BLOCKED_WITH_FRONTIER_PROVEN`

## Environment

- Python: `C:\Program Files\Python311\python.exe`
- Mutagen: `1.48.1` importable=`True`
- Mutagen origin: `C:\Users\rafae\AppData\Roaming\Python\Python311\site-packages\mutagen\__init__.py`
- ffprobe: available=`False`
- native_minimal: available=`True`

## Public Result

- FireTest executed: `True`
- task_run_id: `task_run_a592f87c275440cc89027a70d04dd1e4`
- status: `blocked`
- reason_code: `POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED`
- phase/frontier: `artifact_render` / `POST_COMPILE_OBSERVATION_EXECUTION`
- component/stage: `governed_observation_execution_stage` / `after_post_compile_observation_execution`
- terminal_event_count: `1`
- terminal event: `task_run_event_d9a00d1cd6154a0fa4ba9a705e15c8a4`
- SpeakerTruth safe_to_report_success: `False`

## Corpus / Selection

- candidate_entity_count: `2286`
- selected_entity_count: `2272`
- row_model/projected rows: `2230`
- selected_root_roles: `{'library_root': 2272}`
- project_like_selected_count: `0`

## Post-Compile Execution

- logical/grouped task count: `15610`
- physical groups: `2230`
- physical probes: `336`
- files planned/attempted/succeeded/failed: `2230` / `336` / `335` / `1`
- goals satisfied/unsatisfied: `2339` / `13271`
- fanout_claim_count: `2339`
- evidence_records_created: `3083`
- materialized_observation_bytes: `7335302`
- blocked reason: `POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED`
- logical_tasks_per_physical_probe: `46.458`

## Evidence / Identity

- total media evidence records: `3083`
- per-key evidence counts: not projected in public bounded output for this budget-blocked run
- identity validation reached: `False`
- semantic_identity_evidence_ratio: not reached
- claim-level sample: not available; run blocked before final row semantic validation

## Root Cause

Root cause status: `PROVEN`

First causal frontier: `POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED` in `GovernedObservationExecutionStageService` / post-compile observation execution. The runtime executed legitimate post-compile probes but hit total observation budget after `336` physical probes out of `2230` planned groups.

## Issues

- P1: `R3_01_B_P1_POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED`
- P2: `R3_01_B_P2_BACKEND_AND_KEY_TELEMETRY_PROJECTION_GAP`

## Notes

- Compile-only boundary remained preserved: compile payload metrics show `observation_execution_result_count=0` before post-compile execution.
- Terminality is valid: one `run_blocked` terminal event; later duplicate terminalization was ignored.
- Summary projection still reports media metadata capability as `not_configured` despite physical probes/evidence in authoritative run result. This is classified as P2 telemetry projection inconsistency.
