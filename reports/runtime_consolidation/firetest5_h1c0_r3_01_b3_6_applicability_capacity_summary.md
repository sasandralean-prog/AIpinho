# FireTest 5 H1C0.R3.01 B3.6 - Applicability Capacity Summary

## Mission

- Mission: `H1C0.R3.01.B3.6`
- Mission class: `hybrid_operational_correction`
- Branch: `agent/codex/r3-01-b3-6-applicability-capacity-admission`
- Base main SHA: `496fd9af0cbb21e0ac98670c90b65f0134140b99`
- FireTest 5 executed: `false`
- C gate: `CORRECTIVE_REQUIRED_BEFORE_C`

## Implementation Summary

B3.6 adds a generic opt-in applicability admission boundary before full per-entity applicability resolution. The governed execution stage can now ask a capability/adapter for a cheap admission decision when the capability owns such a method. Media-specific extension/source support remains inside `MediaMetadataObserverAdapter`; the generic stage does not own media extension lists.

The media adapter now exposes `applicability_admission_decision()` and caches backend descriptor supported-extension evidence per adapter instance. Extension remains routing eligibility only, not semantic Truth.

## Public Canary

- Endpoint: `POST /api/v1/analyze`
- Task run: `task_run_a7a71c4e20554640923fe5b96437cea0`
- Operation: `op_2e8f94a9aa694801a8c866d92c165082`
- POST response: client-side timeout at 180 seconds
- Persisted task-run status: `blocked`
- Persisted reason: `POST_COMPILE_APPLICABILITY_TARGET_EXPANSION_EXCEEDED`
- Public result retrieval: `GET /api/v1/task-runs/task_run_a7a71c4e20554640923fe5b96437cea0` returned `200`
- FireTest 5: not executed

## B3.5 vs B3.6

| Metric | B3.5 | B3.6 |
|---|---:|---:|
| reason | `POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED` | `POST_COMPILE_APPLICABILITY_TARGET_EXPANSION_EXCEEDED` |
| target_entity_ref_count | 10000 | 10000 |
| applicability_started_count | 9144 | 5001 |
| applicability_completed_count | 9144 | 5001 |
| resolver_calls_attempted | not projected | 0 |
| resolver_calls_avoided_by_admission | not projected | 5001 |
| admission_decision_count | not projected | 5001 |
| admission_elapsed_ms | not projected | 796 |
| capability_applicable_count | 0 | 0 |
| capability_inapplicable_count | 9143 | 5001 |
| groups_created_count | 0 | 0 |
| physical_probe_count | 0 | 0 |

## Current Frontier

B3.6 eliminated the previous generic full-budget applicability-resolution stall. The canary now blocks earlier and specifically because target expansion/admission is too broad before any eligible media group is found:

`POST_COMPILE_APPLICABILITY_TARGET_EXPANSION_EXCEEDED`

The observed canary still expands:

- `2` execute-observer tasks
- `10000` target entity refs
- `5001` admission decisions before stop
- `5001` expected inapplicable by media backend extension support
- `0` eligible candidates
- `0` groups
- `0` physical probes

## Verdict

`R3_01_B3_6_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_READY`

This is not FireTest readiness. It is a bounded correction that turns the B3.5 dark capacity frontier into a specific admission/target-expansion frontier.

## Remaining Gates

- FireTest 5: `NOT_READY`
- C gate: `CORRECTIVE_REQUIRED_BEFORE_C`
- Remaining P0: none observed
- Remaining P1: `R3_01_B3_6_P1_TARGET_EXPANSION_SELECTION_TOO_BROAD_NO_ELIGIBLE_MEDIA_CANDIDATES`
- Remaining P2: `R3_01_B3_6_P2_PUBLIC_ANALYZE_SYNC_RESPONSE_TIMEOUT_DESPITE_PERSISTED_RESULT`

## No False Success

The canary did not produce physical probes, evidence, semantic validation, or SpeakerTruth success. The block is explicit, terminal, and evidence-backed.
