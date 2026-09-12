# Hybrid Semantic Dependency Foundation

## Status

Sprint 0 foundation for semantic dependency reasoning.

This document defines the invariants that the runtime must preserve while the semantic graph and typed task vocabulary are developed in later sprints.

## Core invariants

1. `MODEL != AUTHORITY`.
2. A model may propose semantic candidates; deterministic gates validate them.
3. Admission is decided by the dependency evaluator, never by the model.
4. `satisfied_with_limitations` means that an upstream outcome is eligible for compatibility evaluation. It does not mean admitted.
5. `knowledge_output` does not imply `safe_for_truth_claim=true`.
6. A limitation blocks only when it is incompatible with a frozen downstream requirement, or when compatibility cannot be established safely.
7. Unknown remains fail-closed.
8. Downstream demand cannot rewrite upstream truth.
9. Deliverables, filenames, phase names, and prose labels are not semantic identifiers unless they exist in governed vocabulary.
10. Capabilities, constraints, downstream uses, semantic properties, and use-safety dimensions are distinct semantic categories and must not be silently reclassified.

## Sprint 0 semantic reasoning boundary

The current boundary is:

```text
Canonical plan + intent
        |
SemanticReasoningPlaybook
        |
ContractBoundSemanticReasoner
        |
candidate only
        |
Deterministic semantic gate
        |
Frozen downstream requirements
        |
PhaseDependencyEvaluationService
        |
Admission decision
```

The playbook provides general reasoning principles, governed vocabulary, generic examples, counterexamples, and confidence calibration. Examples are illustrative only and are not vocabulary authority.

## Minimal typed use-safety vocabulary

Sprint 0 only types use-safety dimensions already emitted by `ArtifactUseSafetyService`.

Each governed use-safety dimension has an observed-state domain and a narrower downstream-requirement domain. An observed state may include `false`, but `false` is never a valid safety requirement. Depending on the dimension, a downstream requirement may accept `true` and, where explicitly governed, `true_with_limitations`.

A dimension discovered in task context but not typed by the authority boundary has no governed requirement states and therefore cannot be selected by the semantic model.

This is intentionally narrower than the planned `TaskSemanticVocabulary`. Sprint 1 will introduce the canonical task-scoped vocabulary, concept types, allowed states, provenance, freeze/hash, and explicit revision semantics.

## Real-model adversarial evidence

The Sprint 0 smoke work deliberately used real local models against the same readonly-analysis prompt.

Observed invalid candidates included:

- a deliverable promoted to downstream use (`analysis_report`);
- an operation mode used as a use-safety state (`readonly_analysis`);
- a capability reclassified as a constraint (`require_read_workspace`);
- vocabulary containers copied as semantic property identifiers.

The deterministic gate must reject all of these regardless of model confidence.

The local Qwen 1.7B path demonstrated conservative/fail-closed behavior after the playbook was supplied. The Qwen2.5 7B path demonstrated stronger confidence calibration but still attempted ontology translation outside the governed vocabulary. Model selection is therefore not an authority shortcut.

## Non-goals of Sprint 0

Sprint 0 does not implement:

- a canonical `TaskSemanticVocabulary`;
- task-local semantic concepts and their state spaces;
- `SemanticWorkUnitContract`;
- `SemanticExecutionGraph`;
- edge-local `SemanticDemand`;
- producer `SemanticOffer`;
- graph revision.

Those belong to subsequent sprints and must build on this foundation rather than introducing FireTest-specific logic.

## Anti-hardcode rule

Runtime architecture must not encode semantic behavior from FireTest names, phase numbers, music-specific paths, corpus names, or artifact filenames.

FireTests are evidence of real workflows, not runtime configuration.
