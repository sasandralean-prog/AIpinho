# AIpinho

AIpinho is a governed cognitive/runtime system for turning natural-language intent into observable, policy-bound execution without claiming more than the runtime can prove.

## Current status ? 2026-09-15

Canonical runtime baseline before this documentation refresh: `820288004562f3ff17ebfe8a074987a1ea6f0e6f`.

The semantic-execution architecture Sprints 0?9 is closed and validated. Its authority chain is:

```text
Prompt / intent
  -> SemanticIntentResolution
  -> GovernanceLifecycle / RuntimeContract
  -> Task + durable TaskRun identity
  -> TaskSemanticVocabulary
  -> SemanticExecutionGraph
  -> EdgeSemanticDemand
  -> governed execution / ArtifactRuntime / Timeline
  -> SemanticOffer + Offer/Demand compatibility
  -> N-way semantics + governed graph revision
  -> Validation + Completion
  -> SemanticTruthFacet
  -> RuntimeTruthEngine
  -> CanonicalOperationState
  -> SpeakerTruth / client output
```

`MODEL != AUTHORITY`. Unknown remains fail-closed. `run_completed` is not sufficient to claim product success.

## Latest FireTest 5 ? full rerun

Campaign: `reports/firetest5_20260915T054806Z/`.

Result: **PARTIAL**.

The campaign reached product phases 1?6. Phases 2, 3 and 5 obtained canonical success; phases 4 and 6 completed operationally but were blocked by RuntimeTruth because timeline sequence integrity was contradictory. Phase 6 correctly refused a success claim with `completion_completed_timeline_has_gaps`.

The run also exposed a cross-phase authority gap: Phase 4 `CanonicalOperationState` was `BLOCKED`, while `PhaseOutcome` still projected `satisfied`; downstream Phase 5/6 dependency admission therefore authorized a producer whose canonical truth was blocked. This is the current highest-value runtime frontier.

Media truth remains intentionally limited: the corpus was physically probed, but governed semantic identity evidence remained insufficient for a full truth claim. The `.m4a`/subprocess encoding issue remains outside the current correction scope.

## Runtime map

- Human-readable map: `docs/architecture/CURRENT_RUNTIME_MAP_20260915.md`
- Image: `docs/architecture/current_runtime_map_20260915.png`
- Context-pack operational map: `AIpinho_context_pack/docs/context/05_RUNTIME_ARCHITECTURE_MAP.md`

## Runtime Doctor

Runtime Doctor is parallel, read-only diagnostic infrastructure. `RuntimeOperatorService` hydrates a `RuntimeSnapshot`; `RuntimeOperatorDoctorService` compares it with an `ExpectedRuntimeContract` and can produce findings/explanations/patch plans. Doctor does **not** execute tools, grant approvals, override RuntimeTruth, or become SpeakerTruth.

## Current engineering frontier

1. Repair event/timeline sequence allocation so terminalization/calibration/guard events cannot collide or leave gaps.
2. Bind `PhaseOutcome` and cross-phase dependency admission to canonical RuntimeTruth/CanonicalOperationState, not producer completion alone.
3. Harden Doctor observability for large completed runs without analysis timeouts or evidence rehydration spikes.
4. Keep FireTest/media behavior generic: no FireTest-, phase-number-, corpus-, or `.m4a`-specific exception in core truth semantics.

## Branch hygiene

Sprints 0?9 are merged into `main`. Their dedicated local worktrees/branches were retired on 2026-09-15; residual local evidence and experimental patches were quarantined under `D:\AIpinho_quarantine\sprints_0_9_20260915`. Remote Sprint branches 7/8/9 were deleted after verifying ancestry in `main`.

## Governing principles

- production code + canonical contracts/config + validated evidence outrank docs;
- execution completion != semantic admission;
- Control success != product success;
- producer outcome does not authorize a consumer by status alone;
- SpeakerTruth cannot claim success above RuntimeTruth;
- Doctor diagnoses, never grants authority;
- FireTest is regression evidence, not runtime configuration.

## Context and handoff

Start with `CURRENT_STATE.md`, then `AIpinho_context_pack/docs/context/00_START_HERE.md` and `AIpinho_context_pack/docs/context/current_state.json`.
