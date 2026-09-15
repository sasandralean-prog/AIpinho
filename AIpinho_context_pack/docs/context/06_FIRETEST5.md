# FireTest 5 — consolidated revalidation — 2026-09-15

## Purpose

FireTest 5 is adversarial product/runtime evidence. It must never become runtime configuration or justify phase-, corpus-, extension- or fixture-specific truth rules.

## Current canonical campaign

Consolidation campaign: `firetest5_runtime_consolidation_20260915T152207Z`.

Canonical reports:

- `reports/runtime_consolidation/runtime_consolidation_final_validation_20260915.md`
- `reports/runtime_consolidation/runtime_consolidation_firetest5_20260915.json`

## Current result

```text
phase_1 = completed_with_limitations
          RuntimeTruth = partial
          PhaseOutcome = satisfied_with_limitations
          safe_to_report_success = false
phase_2 = completed
phase_3 = completed
phase_4 = completed
phase_5 = completed
phase_6 = completed
```

All six TaskRuns had contiguous, unique RuntimeTimeline sequences. Duplicate sequences: `0`. Missing sequences: `0`.

The old Phase 4/6 `runtime_truth_contradiction` did not recur. The old PhaseOutcome bug is closed: blocked/contradictory RuntimeTruth now propagates fail-closed into downstream dependency admission.

## Phase 1 limited-use semantics

`CanonicalOperationState=BLOCKED` prevents Phase 1 from being represented as successful. `RuntimeTruth=partial` preserves bounded evidence. Downstream use may be admitted only as `satisfied_with_limitations` when frozen demand and explicit `use_safety` are compatible.

This distinction is intentional and is not the old cross-phase authority contradiction.

## Roles

`run_role_pipeline` executed in all six TaskRuns. Persisted role runs included deterministic `supervisor_consistency=completed` with `real_inference=false`.

## Doctor

Runtime Doctor completed all six phases, including the former Phase 4/6 large-run cases. Observed campaign latency was approximately 0.4–1.2 seconds.

## Integrity

- target workspace files and bytes unchanged;
- corpus files and bytes unchanged;
- workspace mutations: `0`;
- corpus mutations: `0`;
- repository HEAD unchanged during campaign;
- final queue clean.

## Deferred

The Windows subprocess `cp1252` decoding error surfaced again during media probing. Per project scope it remains deferred and must not be papered over with media-specific core truth logic.

## Historical campaigns

The earlier `firetest5_20260915T054806Z` PARTIAL campaign remains useful root-cause evidence but is superseded for current-state orientation by the consolidation revalidation above.
