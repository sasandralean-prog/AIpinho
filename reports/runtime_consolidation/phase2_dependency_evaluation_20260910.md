# Plan-Derived Phase Dependency Evaluation

## Scope

This report records the generic dependency-evaluation and admission boundary
implemented on top of `4821c32bb42314ebe06864425015dd431ea98076`.
No FireTest was rerun and the corpus was not accessed or modified.

## Requirement source before and after

Before this correction, the branch's first implementation required a
`DownstreamPhaseRequirements` object to be supplied through a static
`PhaseDependencyContractRegistry`. That was safe but not an acceptable normal
authority for dynamically planned task phases: it answered whether a contract
file existed, not what the downstream operation meant.

The normal source is now `PhaseSemanticDemandCompiler`. It consumes the
canonical execution plan, selected execution step, semantic intent graph,
capabilities, side-effect semantics, policy snapshot, and output expectations.
It materializes `DownstreamPhaseRequirements` before dependency evaluation.
Every effective requirement has a source kind, source reference, source field,
and source hash. Missing canonical semantics produces
`INSUFFICIENT_CONTRACT_EVIDENCE`; there is no registry fallback.

The authority chain is:

```text
user language
  -> PromptIntelligence / CanonicalIntentRouter
  -> IntentMap.semantic_intent_graph
  -> TaskContractDraft.intent_map (draft path) or governed TaskRunRequest
  -> TaskRunPlanner
  -> ExecutionPlanPromotionService
  -> CanonicalExecutionPlan + CanonicalExecutionStep
  -> PhaseSemanticDemandCompiler
  -> frozen DownstreamPhaseRequirements + requirement provenance
  -> requirements_sha256
  -> PhaseDependencyEvaluation
  -> PhaseDependencyAdmission
  -> consumer TaskRun bootstrap/intent constraints and evidence refs
```

For workflow phases, `WorkflowRuntimeService.create_for_run()` compiles each
consumer step's demand while creating the workflow, before any upstream phase
can finish. The public cross-run boundary compiles and stores demand immediately
after canonical planning and before reading the upstream phase result.

## Registry role

`PhaseDependencyContractRegistry` remains only as an optional source of fixed
system invariants. An invariant is merged after task demand compilation and can
only strengthen it: accepted statuses and accepted values are intersected;
required capabilities, constraints, and prohibited effects are added; evidence
requirements are ORed; TTL uses the smaller value; limitation handling uses the
stricter classification. A conflict blocks compilation. The registry is empty
by default and never substitutes for absent task/plan semantics.

## Preserved evaluation and admission machinery

- Explicit `PhaseDependencySnapshot`, `DownstreamPhaseRequirements`,
  `PhaseDependencyEvaluation`, and `PhaseDependencyAdmission` models.
- Multidimensional use safety and claim-scoped semantic properties; legacy
  `safe_to_use` is not an admission input.
- Unknown limitation compatibility and missing required evidence fail closed.
- Evaluation and admission are bound to producer/consumer TaskRun, operation,
  dependency, phase, operation type, requirements hash, expiry, and authority
  hash. Replay and cross-TaskRun reuse are rejected.
- Authorized constraints and evidence references are propagated into the
  consumer TaskRun before execution.
- Compiled requirements without plan/execution/source hashes, frozen timestamp,
  or complete per-requirement provenance are rejected as insufficient evidence.
- Cross-session phase-record fallback remains removed.

## Semantic limits of the current canonical plan

The current canonical path can derive requirements represented by the semantic
intent graph and execution plan: planning safety, truth-claim safety, destructive
action safety, prohibited effects, capabilities, evidence, dependency status,
and fixed policy strengthening.

It cannot infer an unstated claim-level property such as an exact acceptable
identity-quality set. Such a property must originate in semantic interpretation
or an output/artifact semantic contract and be projected into the canonical
plan. The compiler does not invent it from a phase number, artifact filename,
or upstream outcome. Until that source exists, a downstream operation that
needs the property must fail closed rather than receive a permissive default.

## Historical FireTest counterfactual

The captured `firetest5_live_20260910T115843Z` evidence contains the Phase 1
result but no canonical Phase 2 request, intent, TaskContract, or execution plan.
Therefore the generic compiler cannot establish what Phase 2 was going to do.
The counterfactual decision is:

```text
INSUFFICIENT_EVIDENCE
PHASE_DEPENDENCY_DOWNSTREAM_CANONICAL_PLAN_REQUIRED
constraints=[]
```

This is not a live Phase 2 execution. No FireTest-specific contract was created.
The captured Phase 1 result was not used to relax or construct requirements.

## Validation

- Focused compiler/evaluator/workflow/public-boundary tests: **44 passed**.
- Adjacent runtime/governance regression: **127 passed, 2 deselected**. The two
  deselected tests were previously proven BASE/CANDIDATE-equivalent failures.
- Intent, draft, and planner adjacency: **30 passed, 2 failed**. Both failures
  reproduce unchanged on baseline `4821c32` and are pre-existing.
- `python -m compileall -q src\aipinho`: PASS.
- `git diff --check`: PASS.
- Production anti-hardcode scan: PASS.

The first expanded run had one non-reproducible asynchronous public-boundary
failure; the test passed alone, passed with its whole file, and the fresh full
adjacent rerun passed all 127 selected tests.

## Out of scope

The historical duplicate event-sequence debt remains unchanged. No corpus,
fixture, FireTest protocol, timeout, or artifact truth rule changed.

## Next live validation

Create a fresh downstream request through the normal semantic interpretation
and canonical planning path. Verify that its compiled demand is frozen before
the upstream snapshot is evaluated, and then validate evaluation/admission and
constraint propagation end to end. If the downstream plan lacks required
claim-level semantics, the next boundary is the canonical semantic-plan source,
not a manual registry entry.
