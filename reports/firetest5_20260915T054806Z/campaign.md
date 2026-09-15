# FireTest 5 Full Rerun ? 2026-09-15

## Verdict

- Campaign status: `PARTIAL`
- Reason: `FINAL_RUNTIME_TRUTH_CONTRADICTION_AND_UPSTREAM_TRUTH_PROPAGATION_GAP`
- Safe to report FireTest success: `false`
- Baseline SHA: `820288004562f3ff17ebfe8a074987a1ea6f0e6f`
- origin/main final: `820288004562f3ff17ebfe8a074987a1ea6f0e6f`

The campaign executed all product phases 1?6. Execution reached the end, but final truth is not green: Phase 6 completed operationally while RuntimeTruth blocked the success claim because the timeline has a duplicate/missing sequence. A second architectural issue was exposed earlier: Phase 4 canonical truth was already blocked, yet its PhaseOutcome remained `satisfied` and downstream phases were admitted.

## Phase matrix

| Phase | Run | Result | Canonical | SpeakerTruth | Safe success | Reason |
|---|---|---|---|---|---:|---|
| phase_1 | `partial` | `completed_with_limitations` | `CREATED` | `evidence_required` | `false` | `timeline_status:partial` |
| phase_2 | `completed` | `completed` | `COMPLETED` | `allowed` | `true` | `timeline_status:completed` |
| phase_3 | `completed` | `completed` | `COMPLETED` | `allowed` | `true` | `timeline_status:completed` |
| phase_4 | `completed` | `completed` | `BLOCKED` | `evidence_required` | `false` | `runtime_truth_contradiction` |
| phase_5 | `completed` | `completed` | `COMPLETED` | `allowed` | `true` | `timeline_status:completed` |
| phase_6 | `completed` | `completed` | `BLOCKED` | `evidence_required` | `false` | `runtime_truth_contradiction` |

## Important observations

- Phase 1 crossed the old performance/stall boundaries and completed with limitations: `CATALOG_READY_WITH_INFERRED_AND_UNKNOWN_IDENTITY`.
- Phase 2 admitted Phase 1 via `ADMITTED_WITH_CONSTRAINTS` and completed safely. This is the boundary that had previously blocked.
- Phases 2 and 3 completed with canonical success.
- Phase 4 produced and validated all three planning artifacts but canonical truth became `BLOCKED` because of a timeline contradiction. Sequence 118 was duplicated.
- Despite Phase 4 canonical block, Phase 5 dependency evaluation authorized Phase 4 and Phase 5 completed. This is a propagation gap between RuntimeTruth/CanonicalOperationState and PhaseOutcome.
- Phase 6 executed and validated all three final artifacts, but sequence 122 was duplicated and sequence 123 was missing. RuntimeTruth returned `blocked`, reason `runtime_truth_contradiction`, contradiction `completion_completed_timeline_has_gaps`.
- SemanticTruth remained ready on the captured final run, but correctly did not override the operational/timeline contradiction.
- Phase 0 predicted `NO_GO_EXPECTED_BLOCK`; calibration events reported `mismatch`, showing the prediction was too pessimistic for the achieved progression.
- A `UnicodeDecodeError` in a cp1252 subprocess reader was observed during Phase 4. It was intentionally not fixed during this FireTest.
- Runtime Doctor analyze timed out for Phase 4 and Phase 6 during post-run diagnosis.
- Phase 6 provenance also exposed a root-path tokenization defect (`...PinhoabacaxiMusicasDesktop. Executar`) while the actual TaskRun workspace remained correct.

## Media truth

- Primary media: `84`
- Physical probes: `84`
- FFprobe: `83/84` successful
- Mutagen: `80/84` successful
- Governed semantic identity: `0/84`
- `music_inventory.csv`: blocked for full Truth by `MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT`
- Catalog safety: `true`
- Planning safety: `true_with_limitations`
- Full truth claim safety: `false`

## Integrity

- Workspace: `1458` files / `544339738` bytes before and `1458` files / `544339738` bytes after.
- Workspace files modified during campaign window: `0`.
- Corpus: `166` files / `287473867` bytes before and `166` files / `287473867` bytes after.
- Corpus files modified during campaign window: `0`.
- Repository HEAD stayed equal to origin/main for the entire campaign.
- No product/workspace mutation was authorized by this campaign.

## Final queue and teardown

- active_runs: `0`
- queued_runs: `0`
- stale_runs: `0`
- pending_approvals: `0`
- dispatcher: `available`
- FireTest coordination lock released/preserved in audit history.
- Campaign-started AIpinho API stopped; port 9088 has no listener.

## Final assessment

This is substantial runtime progress compared with the previous campaigns: all six phases were reached and terminalized, including Phase 5 and Phase 6. However, the correct global verdict is not PASS. The new truth layers successfully refuse to equate `run_completed` with product truth, but FireTest exposed that cross-phase admission still trusts a PhaseOutcome that can omit a canonical RuntimeTruth block. The next correction should address event sequencing/terminalization and propagate canonical truth authority into PhaseOutcome/dependency admission before another full rerun.
