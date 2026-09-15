# FireTest 5 ? 2026-09-15

## Purpose

FireTest 5 is adversarial product/runtime evidence. It must never become runtime configuration or justify FireTest/media/phase-specific truth rules.

## Latest canonical campaign

Campaign directory: `reports/firetest5_20260915T054806Z/`.

Global verdict: **PARTIAL**. The product progression reached phases 1?6 for the first time in this update.

- Phase 0: `NO_GO_EXPECTED_BLOCK`; later calibration events marked the prediction as mismatch.
- Phase 1: `completed_with_limitations`, catalog/planning limited by semantic identity evidence.
- Phase 2: canonical success.
- Phase 3: canonical success.
- Phase 4: operationally completed, but canonical state `BLOCKED` by RuntimeTruth contradiction.
- Phase 5: canonical success; historically this phase had timed out before TaskRun creation.
- Phase 6: operationally completed with all final artifacts validated, but canonical state `BLOCKED`; SpeakerTruth refused success.

Final contradiction: `completion_completed_timeline_has_gaps`. Phase 6 had duplicate event sequence `122` and no sequence `123`. Phase 4 had duplicate sequence `118`.

## Current architectural finding

Phase 4 exposed an authority propagation gap: CanonicalOperationState was blocked while projected PhaseOutcome remained `satisfied`; Phase 5/6 admitted that dependency. The next correction must bind cross-phase admission to canonical producer truth.

## Media boundary

Physical media evidence was collected, but governed semantic identity remained insufficient for a full truth claim. Catalog use is allowed; planning is allowed with limitations; full truth is not. The `.m4a`/subprocess encoding issue is intentionally deferred.

## Integrity

Latest campaign mutated neither the target workspace nor corpus. Final runtime queue was clean and the campaign API was stopped after teardown.

## Evidence

- `reports/firetest5_20260915T054806Z/campaign.md`
- `reports/firetest5_20260915T054806Z/verdict.json`
- `reports/firetest5_20260915T054806Z/sequence_audit.json`
