# Semantic Graph Revision Foundation

## Status

Sprint 7 foundation, built on the completed Sprint 0–6 authority chain.

Sprint 7 introduces explicit graph evolution without mutating historical graph
snapshots or the semantic contracts produced under them.

## Core invariant

Graph revision creates a new canonical graph.

It does not edit the historical graph in place.

```text
Parent SemanticExecutionGraph
        |
        |  SemanticGraphRevisionProposal
        v
Deterministic Revision Gate
        |
        +---- SemanticGraphRevision
        |
        v
Child SemanticExecutionGraph
```

The revision record binds exact parent and child graph authority hashes.

## Revision intent

A SemanticGraphRevisionProposal contains:

- parent_graph_id;
- parent_graph_authority_sha256;
- parent_revision_id when applicable;
- revision_number;
- non-empty reason;
- provenance;
- work-unit additions;
- edge additions;
- explicit edge removals;
- explicit work-unit removals.

The deterministic revision_intent_sha256 excludes incidental proposal identity
and timestamp fields. The same parent plus the same semantic revision intent
produces the same child graph and revision authority.

## Deterministic identities

New WorkUnit IDs are derived from:

- parent graph authority hash;
- revision number;
- addition key;
- complete typed addition payload.

New edge IDs are derived from:

- parent graph authority hash;
- revision number;
- addition key;
- resolved producer and consumer IDs;
- edge relation and required state.

Model- or caller-provided local addition keys never become canonical IDs.

## Validation

The revision gate verifies:

- parent graph authority;
- TaskSemanticVocabulary authority and binding;
- exact proposal parent graph binding;
- non-empty reason and provenance;
- at least one explicit change;
- known removal targets;
- explicit removal of incident edges before WorkUnit removal;
- governed work modes, capabilities and effects;
- unique source-step binding in the resulting child graph;
- valid edge endpoints;
- no self edges;
- no duplicate edge semantics;
- DAG acyclicity.

Unknown or mismatched authority fails closed.

## Historical immutability

Applying a revision returns a new child graph and revision record.

It does not mutate:

- the parent SemanticExecutionGraph;
- historical EdgeSemanticDemand objects;
- historical SemanticOffer objects;
- historical OfferDemandCompatibility objects;
- historical N-way topology projections.

Those contracts remain bound to the graph SHA under which they were produced.

## Demand recompilation boundary

Every child edge is listed in:

```text
edges_requiring_demand_recompile
```

The graph authority hash changes across a revision, so even structurally
unchanged edges cannot reuse parent-bound Demand objects. Activation
recompiles every child Demand against the child graph.

Sprint 7 does not silently copy a Demand from another edge or parent graph.
For a newly discovered consumer whose source step did not exist in the
original canonical plan, deterministic compilation produces an honest partial
Demand instead of inventing semantic requirements.

## Source semantics lineage

The child graph receives a new source_semantics_sha256 derived from:

- parent source_semantics_sha256;
- parent graph authority SHA;
- revision_intent_sha256.

This preserves lineage without modifying the SemanticExecutionGraph v1 schema
or invalidating hashes of already persisted historical graphs.

## Activation and history

SemanticGraphActivationService activates a validated child graph
transactionally.

Before activation it verifies:

- parent, child and revision authorities;
- exact parent/child revision bindings;
- monotonic revision number and parent revision chain;
- authorities and graph bindings of current Demands, Offers,
  Compatibilities, neighborhoods and joins.

It then recompiles all child-graph Demands in an isolated copy. Only after
successful recompilation does it:

- archive the complete parent graph and its graph-bound contracts in a
  SemanticGraphHistorySnapshot;
- append the canonical revision record;
- activate the child graph;
- install child-bound Demands;
- clear active Offers, Compatibilities and N-way projections so parent
  contracts cannot leak into child evaluation.

Activation failure leaves the active parent state unchanged.

Revision chains are monotonic and explicit:

```text
initial graph
  -> revision 1 / child 1
  -> revision 2 / child 2
  -> revision 3 / child 3
```

Each revision references the immediately preceding revision and graph hash.
Historical snapshots remain independently authority-bound.


## Sprint 8 handoff — Completion, SpeakerTruth and Doctor

Sprint 8 consumes the immutable semantic history established through Sprints
0–7.

It may derive completion and user-facing operational truth from:

- the currently active graph and revision;
- historical graph snapshots;
- producer SemanticOffers;
- edge-local SemanticDemands;
- Offer/Demand Compatibility decisions;
- N-way join evaluations;
- unresolved requirements, limitations and missing truth.

Sprint 8 must not rewrite historical graph revisions or reinterpret an old
Offer under a different graph authority.

The intended boundary is:

```text
Execution / evidence / semantic history
        |
        v
Completion evaluation
        |
        +---- Doctor facets
        |
        v
SpeakerTruth
        |
        v
user-facing operational truth
```

Control completion and product truth remain separate. A terminal TaskRun or a
successfully activated graph revision is not sufficient by itself for a
user-facing success claim.
