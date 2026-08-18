# FireTest 5 ? H1C0.R2.3 Phase 1 Dedicated Report

Generated at: `2026-08-14T01:09:08.302734+00:00`

## Verdict

Phase 1 is **BLOCKED**, but the H1C0.R2.3 finalization repair is **READY**.

This report is the baseline before the requested non-canonical Phase 2?6 diagnostic test.

## Runtime Identity

- `task_run_id`: `task_run_72f9f0706d27438eb74fb4988346e9fd`
- `operation_id`: `op_47ef6bfb17a1448f9ddf47fba19adf49`
- `client_response_status`: `accepted_running`
- `client_response_time_ms`: `6272`
- `run_status`: `BLOCKED`
- `result_status`: `blocked`
- `result_json_exists`: `True`
- `result_endpoint_status_code`: `200`
- `finished_at`: `2026-08-14T01:04:35.989027+00:00`
- `terminal_event_count`: `1`
- `terminal_event_types`: `['run_blocked']`

## Truth / Safety

- `truth.safe_to_report_success`: `False`
- Canonical Phase 2 allowed: `false`
- Reason: Phase 1 blocked and did not satisfy Validation/Completion/Speaker Truth.

## Music Inventory

- `status`: `blocked`
- `semantic_contract_status`: `partial`
- `reason_code`: `MUSIC_INVENTORY_PARTIAL_EVIDENCE`
- `expected_rows`: `1051`
- `selected_rows`: `100`
- `bound_rows`: `100`
- `partial_rows`: `100`
- `evidence_ref_count`: `100`
- `row_evidence_coverage.status`: `satisfied`
- `safe_to_use`: `False`

## Evidence Package

- `evidence_phase1.status`: `ready`
- `evidence_phase1.semantic_contract_status`: `satisfied`
- `evidence_phase1.safe_to_use`: `True`

## Endpoint Timings

- `summary`: 2176 ms
- `truth`: 1204 ms
- `events`: 6562 ms
- `artifacts`: 1032 ms
- `result`: 301 ms
- `queue_after`: 858 ms

## Storage / Queue

- `queue.status`: `ok`
- `active_runs`: `0`
- `large_run_count`: `0`
- `missing_index_count`: `0`
- `run_json_bytes`: `156870`
- `result_json_bytes`: `877`

## Diagnostic Note

The requested Phase 2?6 execution after this report is **non-canonical diagnostic override**. It must not be interpreted as FireTest progression, because Phase 1 is blocked.
