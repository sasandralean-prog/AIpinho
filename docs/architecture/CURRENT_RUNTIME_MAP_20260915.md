# AIpinho Current Runtime Map ? 2026-09-15

> Verified against production code on `main` at baseline `820288004562f3ff17ebfe8a074987a1ea6f0e6f` and cross-checked against the GitHub default branch. Code and runtime evidence remain authoritative.

## End-to-end authority map

```text
[USER / CLIENT]
      |
      v
[FastAPI public ingress]
 governance_lifecycle_router.py
 POST /api/v1/chat
      |
      v
[CanonicalPublicChatService]
 - route surface adapter
 - cannot invent operational truth
      |
      v
+---------------- GOVERNANCE LIFECYCLE ----------------+
| SemanticIntentResolutionService                      |
|        |                                              |
|        v                                              |
| CanonicalOperationContract                           |
|        |                                              |
|        v                                              |
| EffectivePolicyDecisionService                       |
|        |                                              |
|        +--> ContextDiscoveryGate / PreviewQuality    |
|        +--> CanonicalApprovalService (if ASK)        |
|        |                                              |
|        v                                              |
| CanonicalRuntimeService -> executable plan preview   |
+-------------------------------------------------------+
      |
      | requires Task / governed execution
      v
[TaskRuntimeService / Universal Task Runtime boundary]
      |
      +--> TaskBootstrapRuntimeService
      |      -> Task / TaskRun / Operation durable identity
      |
      +--> TaskRunPlanner / ExecutionPlanPromotion
      |
      +--> S1 TaskSemanticVocabularyCompilerService
      +--> S2 SemanticExecutionGraphCompilerService
      +--> S3 EdgeSemanticDemandCompilerService
      |      (frozen before operational execution graph)
      |
      v
[Queue / Guard / Policy / Approval checks]
      |
      v
[SupervisedExecutionLoop]
      |
      +--> TaskRunExecutor
      |     -> GovernedTaskStepRunner
      |     -> governed tools / domain executors
      |
      +--> RuntimeTimeline events
      +--> ArtifactRuntime / evidence binding
      +--> Validation
      |
      v
[S4 SemanticOffer / result projection]
      |
      v
[S5 OfferDemandCompatibility]
      |
      +--> S6 N-way fan-in/fan-out / joins
      +--> S7 governed graph revision + immutable history
      |
      v
[Completion / SemanticCompletionTruthService]
      |
      v
[SemanticTruthFacet]
      |
      v
[RuntimeTruthEngine]  <----- operational final-truth authority
 - completion evidence
 - validation evidence
 - timeline/terminal evidence
 - artifact producer binding/orphans
 - semantic facet
 - contradictions / missing evidence
      |
      v
[CanonicalOperationStateService]
 - single status mirror for lifecycle/UI/safe-success
 - COMPLETED only when RuntimeTruth is safe
      |
      v
[CanonicalSpeakerTruthService / publication adapters]
      |
      v
[Chat / Mobile / API / Launcher output]

                    PARALLEL READ-ONLY DIAGNOSTIC PLANE

TaskRun / public runtime payload / expected contract
      |
      v
[RuntimeOperatorService]
 -> RuntimeSnapshot
 -> hydrates Timeline + RuntimeTruth when TaskRun is supplied
      |
      v
[RuntimeOperatorDoctorService]
 -> regression matrix
 -> findings/evidence/recommendations
 -> optional RuntimeExplainerService
 -> optional RuntimePatchPlannerService (plan only)

Doctor authority ceiling:
  diagnose/explain/plan != approve/execute/patch/override Truth
```

## Authorities and non-authorities

| Boundary | Concrete authority | What it may decide | What it may NOT decide |
|---|---|---|---|
| Prompt semantics | `SemanticIntentResolutionService` | intent/state-effect classification | execution success |
| Operational contract | `GovernanceLifecycleService` + `CanonicalOperationContract` | operation type, readonly/mutation contract | observed runtime completion |
| Permission | `EffectivePolicyDecisionService` | allowed/ask/denied | whether work actually executed |
| Approval | `CanonicalApprovalService` + persisted approval services | permission gate for approved side effects | validation/completion truth |
| Task identity | `TaskBootstrapRuntimeService` / `TaskRunStore` | durable Task/TaskRun/Operation identity | semantic sufficiency |
| Semantic vocabulary | `TaskSemanticVocabularyCompilerService` | frozen typed task concepts/states | observed outcome |
| Work graph | `SemanticExecutionGraphCompilerService` | semantic work-unit topology | producer evidence |
| Edge demand | `EdgeSemanticDemandCompilerService` | consumer-local requirements | producer success |
| Execution | `TaskRuntimeService` + `SupervisedExecutionLoop` | governed runtime progression | user-facing success by itself |
| Timeline | `RuntimeTimelineService` | ordered operational evidence | semantic interpretation alone |
| Artifacts | ArtifactRuntime + registry/evidence binding | artifact lifecycle/provenance | terminal success alone |
| Offer | `SemanticOfferCompilerService` | producer semantic offer from governed evidence | consumer admission |
| Compatibility | `OfferDemandCompatibilityService` | per-edge admit/constrain/block | global graph truth |
| N-way | `SemanticNWayProjectionService` | fan-in/fan-out/join semantic projection | historical graph reuse without revision authority |
| Revision | `SemanticGraphRevisionAuthorityService` | valid child graph/revision history | retroactive authority over active child graph |
| Semantic completion | `SemanticCompletionTruthService` | `ready/constrained/blocked/insufficient_evidence` facet | override operational contradictions |
| Operational truth | `RuntimeTruthEngine` | final safe-success truth from runtime evidence | mutate runtime state |
| Canonical status | `CanonicalOperationStateService` | UI/lifecycle status mirror from Truth | create independent success authority |
| Speaker | `CanonicalSpeakerTruthService` / publishers | what may be claimed to user | claim above RuntimeTruth |
| Doctor | `RuntimeOperatorDoctorService` | diagnose divergence, explain, propose patch plan | execute tools, grant approval, override Truth |

## Current FireTest-discovered gaps

1. **Timeline allocation:** terminalization/guard/calibration events can collide. Latest evidence: Phase 4 duplicate `118`; Phase 6 duplicate `122` plus missing `123`.
2. **Cross-phase truth propagation:** Phase 4 canonical state was blocked by RuntimeTruth, but `PhaseOutcome` projected `satisfied` and downstream dependency admission authorized it.
3. **Doctor large-run observability:** full Doctor analysis timed out on large Phase 4/6 snapshots.
4. **Subprocess encoding:** cp1252 reader failure surfaced during Phase 4; intentionally deferred from the current correction scope.
5. **Prompt root tokenization:** Phase 6 provenance captured a textual suffix in one root-role observation; actual TaskRun workspace remained correct.

## Invariants

- `MODEL != AUTHORITY`.
- Unknown is fail-closed.
- Producer completion does not authorize a consumer.
- Demand is edge-local.
- Same Offer can be admitted, constrained or blocked differently per edge.
- Historical graph truth cannot authorize a revised active graph.
- `run_completed` does not imply safe success.
- Runtime Doctor diagnoses; RuntimeTruth decides safe operational claims.
