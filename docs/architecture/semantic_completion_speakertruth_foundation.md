# Semantic Completion / SpeakerTruth Foundation

## Status

Sprint 8 foundation over the completed Sprint 0-7 semantic authority chain.

This layer does not create a second SpeakerTruth authority.

`RuntimeTruthEngine` remains the canonical operational truth resolver. Sprint 8
adds one governed semantic facet for RuntimeTruth to consume.

## Authority chain

```text
TaskSemanticVocabulary
        ↓
SemanticExecutionGraph
        ↓
EdgeSemanticDemand
        ↓
SemanticOffer
        ↓
OfferDemandCompatibility
        ↓
N-way Join Evaluation
        ↓
Graph Revision / Active Graph
        ↓
SemanticTruthFacet
        ↓
RuntimeTruthEngine
        ↓
SpeakerTruth / CanonicalOperationState / UI
```

## SemanticTruthFacet

The facet answers only:

> Does the active semantic graph support a user-facing claim of successful
> completion?

It does not decide TaskRun lifecycle, validation, artifact correctness or
terminality by itself.

Supported facet states:

- `not_applicable` — no semantic graph exists for this run;
- `ready` — all required semantic relations are admitted without unresolved
  evidence or disclosure-bearing constraints;
- `constrained` — required relations are admissible only with explicit
  constraints/disclosures;
- `blocked` — at least one required relation is explicitly incompatible, or
  active semantic authority is invalid;
- `insufficient_evidence` — required Demand/Compatibility/Join evidence is
  absent, partial or invalidated by graph revision.

`safe_to_report_success` is true only for `ready` and
`not_applicable`.

A constrained semantic graph may support continued downstream processing but
does not authorize an unqualified user-facing success claim.

## Open-world semantics

Absence remains unknown.

Examples:

- missing Compatibility is unresolved, not blocked;
- partial Demand is unresolved, not false;
- missing join evaluation for multi-producer required fan-in is unresolved;
- graph revision invalidation requires fresh projection before success can be
  reported.

Explicit negative compatibility remains negative evidence.

## Revalidation

SemanticCompletionTruthService revalidates active contracts before using them:

- SemanticExecutionGraph authority;
- Demand authority and exact graph/edge binding;
- Offer authority and exact graph binding;
- Compatibility authority plus exact Offer/Demand hash binding;
- required multi-edge join authority and graph binding.

A valid contract from another graph is not admissible evidence.

## Revision semantics

When Sprint 7 activates a child graph, parent Offers, Compatibilities and N-way
projections become historical.

Until fresh semantic result projection exists for the child graph,
SemanticTruthFacet is `insufficient_evidence`.

Historical truth is preserved but cannot authorize a claim about the active
child graph.

## RuntimeTruth integration boundary

The foundation service is intentionally isolated first.

Integration with RuntimeTruthEngine must preserve:

- RuntimeTruthEngine as the single operational SpeakerTruth authority;
- active/non-terminal runs must not be converted to failure merely because
  terminal semantic evidence does not exist yet;
- a completed result cannot be safe when semantic facet is blocked,
  constrained or insufficient;
- semantic disclosures must be visible to Runtime Doctor and user-facing truth
  surfaces;
- existing non-semantic runs remain compatible through
  `not_applicable`.

## Runtime Doctor boundary

Runtime Doctor should diagnose, not decide independently.

Sprint 8 integration should add explicit violations for cases such as:

- canonical COMPLETED while semantic facet is not safe;
- SpeakerTruth safe=true while semantic facet is blocked or unresolved;
- completed lifecycle with semantic projection invalidated by graph revision;
- invalid semantic authority referenced by current runtime truth.

The Doctor must surface the exact semantic reason codes and graph identity.

## Sprint 9 handoff

Sprint 9 should use this foundation in cross-domain synthetic workflows to
prove that no FireTest-, media-, phase-number- or domain-specific rule is
required for final truth.
