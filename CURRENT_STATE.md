# AIpinho Current State — 2026-09-15

## Authority note

This file is an orientation snapshot. Current production code, canonical configuration/contracts and validated runtime evidence remain authoritative.

## Repository baseline

- Repository: `sasandralean-prog/AIpinho`
- Branch: `main`
- Runtime consolidation implementation commit: `6126a73a9ddfc054fe527174fe4df16740b9d1e0`
- Semantic Sprints 0–9: `COMPLETE` and integrated into the canonical runtime.
- Runtime + roles consolidation: `COMPLETE / VALIDATED`.
- Canonical post-consolidation focused regression: `174 passed / 0 failed` after reboot.
- Sprint 0–9 dedicated branches/worktrees: retired after merge; residual evidence remains quarantined outside the tracked repository.

## Five canonical authorities

1. **Human operator** — grants authority, approvals and scope.
2. **Trusted dispatcher** — validates identity/operation/arguments/scope and invokes fixed capabilities.
3. **Local execution broker** — routes already-authorized operations to Git/tests/build/FireTest/AIpinho.
4. **AIpinho runtime** — owns meaning, intent, contract, planning, governed execution, evidence binding, validation, RuntimeTruth and SpeakerTruth ceiling.
5. **Evidence/result layer** — provides auditable outputs, diagnostics and validation evidence without inventing success.

The dispatcher/broker may not become a second semantic planner or orchestration runtime.

## Canonical runtime

```text
public ingress
  → CanonicalPublicChatService
  → SemanticIntentResolution / GovernanceLifecycle
  → OperationContract / Policy / Approval
  → TaskBootstrap + durable TaskRun
  → TaskRunPlanner / ExecutionPlanPromotion
  → TaskSemanticVocabulary
  → SemanticExecutionGraph
  → EdgeSemanticDemand
  → SupervisedExecutionLoop
  → TaskRunExecutor / GovernedTaskStepRunner
  → domain executors + TaskRuntime-bound RolePipeline children
  → RuntimeTimeline / artifacts / validation / TaskRunResult
  → SemanticOffer / Offer-Demand compatibility
  → N-way semantics / governed graph revision
  → SemanticCompletionTruth / SemanticTruthFacet
  → RuntimeTruthEngine
  → CanonicalOperationState
  → CanonicalSpeakerTruth
  → client output
```

Roles/models are subordinate components inside this runtime. `RuntimeContractsV2`, `PlannerV2`, and `RuntimeDispatcherV2` are compatibility/introspection, not a second execution plane.

## Latest FireTest 5 revalidation

Canonical summary: `reports/runtime_consolidation/runtime_consolidation_final_validation_20260915.md`.

```text
phase_1 = completed_with_limitations / RuntimeTruth partial
          PhaseOutcome satisfied_with_limitations
          safe_to_report_success = false
phase_2 = completed / RuntimeTruth completed
phase_3 = completed / RuntimeTruth completed
phase_4 = completed / RuntimeTruth completed
phase_5 = completed / RuntimeTruth completed
phase_6 = completed / RuntimeTruth completed
```

Across all six phases:

- RuntimeTimeline sequence gaps: `0`
- duplicate sequences: `0`
- `run_role_pipeline` executed: `6/6 TaskRuns`
- persisted supervisor consistency pass: `completed`, deterministic, `real_inference=false`
- Runtime Doctor: completed all phases, including former Phase 4/6 problem cases
- workspace mutations: `0`
- corpus mutations: `0`
- final runtime queue: clean

Phase 1 is intentionally not a success claim. `CanonicalOperationState=BLOCKED` prevents success/UI claims while `RuntimeTruth=partial`; edge-local downstream use may still be admitted only as `satisfied_with_limitations` when explicit use-safety is compatible.

## Bugs closed by the consolidation

- RuntimeTimeline event sequence allocation race / duplicate-gap failure.
- blocked/contradictory RuntimeTruth failing to constrain `PhaseOutcome` and downstream admission.
- large-run Runtime Doctor evidence rehydration/timeout path.
- specialized readonly artifact service owning a duplicate lifecycle/result/Truth path.
- planned `run_role_pipeline` appearing in the plan without executing in specialized artifact flows.
- role pipeline binding/authority ambiguity and deterministic supervisor inconsistency.
- root-role provenance tokenization suffix issue.

## Deferred

- Windows subprocess `cp1252` decoding failure observed in `.m4a`/media probing remains explicitly deferred.

## Genome / runtime map

- Genome: `genome/00_manifest.json` — version `2.0`, regenerated from the consolidated runtime.
- GitHub folder audit: `genome/reports/github_folder_audit_20260915.md`.
- Runtime map: `docs/architecture/CURRENT_RUNTIME_MAP_20260915.md`.
- Context map: `AIpinho_context_pack/docs/context/05_RUNTIME_ARCHITECTURE_MAP.md`.

## Current engineering frontier

There is no open P0/P1 from the FireTest 5 consolidation wave. New work should extend the single canonical runtime rather than introduce parallel planners, dispatchers, role runtimes or truth authorities.

Near-term priorities are evidence-backed cleanup/evolution of compatibility surfaces, continued semantic/runtime capability growth, documentation/Genome synchronization, and explicitly scoped treatment of the deferred media-reader encoding issue if/when it becomes relevant.

## Invariants

- `MODEL != AUTHORITY`.
- Unknown is fail-closed.
- Execution completion != semantic admission.
- Producer completion does not authorize consumer usage.
- Demand is edge-local; Offer/Demand compatibility is evaluated per edge.
- Historical graph truth cannot authorize a revised active graph.
- `run_completed != safe success`.
- Doctor diagnoses; RuntimeTruth governs safe operational claims.
- FireTest is regression evidence, not runtime configuration.
