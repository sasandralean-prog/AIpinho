# Semantic Offer and Offer/Demand Compatibility Foundation

## Status

Sprints 4 and 5 canonical foundation.

This layer extends:

- Sprint 0 deterministic/model governance;
- Sprint 1 TaskSemanticVocabulary;
- Sprint 2 SemanticExecutionGraph;
- Sprint 3 EdgeSemanticDemand.

## Sprint 4 — Producer-local SemanticOffer

SemanticOffer records only what a specific producer WorkUnit actually
established.

Offer construction is independent of downstream Demand.

```text
WorkUnit execution evidence
        |
        v
ObservedWorkUnitSemanticOutcome
        |
        v
SemanticOffer
```

A TaskRun-wide result is not copied into every WorkUnit. WorkUnit attribution
must be explicit.

The runtime projection reads semantic truth only from a typed
semantic_outcome envelope in source-step output summaries. Similar-looking
free-form output does not gain semantic authority.

Offer may contain:

- use-safety observations;
- epistemic property observations;
- allowed downstream uses;
- evidence domains;
- observed effects;
- evidence/artifact refs;
- limitations and missing truth;
- required disclosures and risk constraints;
- source provenance.

Missing positive observations remain unknown. Absence is not a negative
observation.

A WorkUnit with terminal execution but no attributable semantic signal may
produce an Offer with status unknown rather than fabricated truth.

## Sprint 5 — Edge-local compatibility

Compatibility evaluates one immutable SemanticOffer against one immutable
EdgeSemanticDemand.

```text
Producer WorkUnit ---- SemanticOffer
       |                    |
       |                    |
       +---- Edge ---- SemanticDemand ---- Consumer
                            \          /
                             \        /
                         Compatibility
```

Compatibility authority binds exact:

- semantic graph authority;
- edge identity;
- Offer ID and authority SHA;
- Demand ID and authority SHA;
- producer and consumer IDs;
- decision dimensions and constraints.

Compatibility never rewrites Offer or Demand.

## Decisions

Supported decisions:

- admitted;
- admitted_with_constraints;
- blocked;
- insufficient_evidence.

Observed incompatible values can block.

Missing values, absent positive-list entries and epistemic unknown values are
insufficient evidence, not false.

Limitations/disclosures may produce admitted_with_constraints when all actual
requirements are otherwise satisfied.

The same Offer may be admitted for one consumer and blocked for another.

## Runtime projection

Terminal TaskRun truth is computed first.

Only afterwards:

```text
TaskRunResult
    |
    v
Observed WorkUnit outcomes
    |
    v
SemanticOffer[]
    |
    +---- frozen EdgeSemanticDemand[]
             |
             v
OfferDemandCompatibility[]
```

Failure to project an Offer does not retroactively change TaskRun terminal
truth. It only means downstream semantic admission lacks that producer Offer.

## FireTest transition

The current FireTest phase-to-phase implementation still has legacy cross-run
PhaseOutcome / PhaseSemanticDemand compatibility. Sprints 4 and 5 do not
pretend that TaskRun-local WorkUnit contracts already replace every cross-run
relationship.

Regression keeps the FireTest Phase 1 → Phase 2 contract green while the new
Offer/Demand architecture remains generic and phase-number independent.

## Sprint 6 handoff — N-way semantics

Sprint 6 must generalize the already independent contracts to topology:

- fan-out: one Offer evaluated against multiple edge Demands;
- fan-in: one consumer receiving Offers from multiple producers;
- joins: consumer admission based on a set of incoming edge compatibilities;
- mixed decisions: some incoming edges admitted, constrained, blocked or
  unresolved;
- outgoing demand forecasts without assuming one successor;
- no N-1 / N / N+1 positional authority.

Sprint 6 should introduce topology/neighborhood and join-evaluation contracts.
It must not mutate historical Offers, Demands or Compatibility records and
must not perform the graph revision work reserved for Sprint 7.
