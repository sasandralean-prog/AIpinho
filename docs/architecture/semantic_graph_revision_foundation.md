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

Newly added edges are listed in:

```text
edges_requiring_demand_recompile
```

Sprint 7 does not silently copy a Demand from another edge or parent graph.
The Sprint 3 demand compiler must create a new edge-local Demand for the child
graph before downstream compatibility can be evaluated.

## Source semantics lineage

The child graph receives a new source_semantics_sha256 derived from:

- parent source_semantics_sha256;
- parent graph authority SHA;
- revision_intent_sha256.

This preserves lineage without modifying the SemanticExecutionGraph v1 schema
or invalidating hashes of already persisted historical graphs.

## Current boundary

The foundation deliberately does not yet activate the child graph inside a
TaskRun automatically.

Runtime activation must preserve a graph history and must not mix historical
Offers, Demands or Compatibilities from the parent graph into child-graph
evaluation.

That activation/history layer is the next Sprint 7 step.
