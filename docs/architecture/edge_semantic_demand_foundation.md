# Edge Semantic Demand Foundation

## Status

Sprint 3 canonical foundation for consumer-local requirements on semantic graph edges.

This layer extends:

- Sprint 0 deterministic/model governance;
- Sprint 1 TaskSemanticVocabulary;
- Sprint 2 SemanticExecutionGraph.

It does not replace or mutate any of those authorities.

## Core invariant

Demand describes what one consumer needs from one producer on one exact edge.

Demand does not describe producer truth.

```text
Producer WorkUnit
      |
      +---- SemanticDependencyEdge ----> Consumer WorkUnit
                        |
                        +---- EdgeSemanticDemand
```

The same producer may have different demands on different outgoing edges.

## Authority binding

Each EdgeSemanticDemand is bound to:

- edge_id;
- semantic_graph_id;
- semantic_graph_authority_sha256;
- producer_work_unit_id;
- consumer_work_unit_id;
- TaskSemanticVocabulary binding;
- consumer source-step provenance;
- requirement content;
- its own authority_sha256.

Graph authority and demand authority are independent.

## Deterministic compilation

The deterministic compiler reads only typed consumer semantics such as:

- required_downstream_uses;
- required_use_safety;
- required_semantic_properties;
- required_evidence_domains;
- required_upstream_effects;
- prohibited_upstream_effects;
- evidence_required;
- base_constraints;
- risk_constraints.

It does not derive requirements from:

- phase numbers;
- node position;
- filenames;
- deliverable names;
- free-form labels.

A semantic edge with missing requirement semantics may produce a partial demand.
Partial means unresolved requirement semantics, not no requirement.

## Model-assisted backward interpretation

A model may propose missing requirements only for a partial demand.

The deterministic gate:

- validates every identifier/state against the frozen vocabulary;
- prevents evidence dependency weakening;
- prevents contradiction of explicit consumer requirements;
- requires confidence and rationale;
- freezes the accepted demand with deterministic authority.

A ready deterministic demand is never reopened for model negotiation.

## Runtime binding

TaskRunPlan stores edge_semantic_demands separately from SemanticExecutionGraph.

During TaskRun construction:

```text
TaskSemanticVocabulary
    ↓
SemanticExecutionGraph
    ↓
deterministic EdgeSemanticDemand[]
    ↓
Operational ExecutionGraph
```

Model interpretation is not invoked during ordinary create_run.

## Transitional FireTest compatibility

The current FireTest 5 phase-to-phase contract is still cross-TaskRun and uses
the legacy PhaseOutcome / PhaseSemanticDemand / dependency evaluator path.

Sprint 3 does not pretend that a TaskRun-local semantic edge has already
replaced that cross-run relationship.

Regression coverage proves the new edge-local architecture coexists with the
existing FireTest Phase 1 → Phase 2 semantic contract without weakening it.

Cross-run and N-way unification belongs to the later Offer/Demand/Compatibility
and graph semantics work.

## Sprint 4 + 5 handoff

Sprint 4 introduces SemanticOffer as a producer-local, evidence-backed,
immutable semantic result contract.

Sprint 5 introduces edge-local compatibility:

```text
Producer WorkUnit
      |
      +---- SemanticOffer
      |
      +---- Edge ---- SemanticDemand ----> Consumer
                    \                  /
                     \                /
                      Compatibility
```

Required invariants:

- Demand must never mutate Offer.
- Offer must never be synthesized from Demand.
- Compatibility must never rewrite either input.
- The same Offer may be admitted for one Demand and blocked for another.
- Missing producer evidence remains unknown, not false.
- Historical producer truth remains immutable.
- Compatibility authority must bind exact Offer and Demand authority hashes.
