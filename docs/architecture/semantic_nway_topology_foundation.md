# N-way Semantic Topology Foundation

## Status

Sprint 6 foundation, built on the completed Sprint 0–5 authority chain.

This layer is intentionally read-only with respect to the semantic graph.
Dynamic graph revision remains Sprint 7.

## Purpose

Sprint 6 removes the assumption that semantic dependency is a single linear
N-1 → N → N+1 chain.

The topology layer supports:

- fan-out: one producer feeding multiple consumers;
- fan-in: one consumer depending on multiple producers;
- required and optional incoming edges;
- join decisions over multiple edge-local compatibility records;
- outgoing demand references without assuming one successor.

## Core rule

N-way semantics aggregate edge-local decisions, not producer truths.

```text
Producer A -- Offer A -- Edge A -- Demand A --\
                                                \
                                                 Consumer Join
                                                /
Producer B -- Offer B -- Edge B -- Demand B --/
```

Each Offer, Demand and Compatibility remains independently immutable and
authority-bound.

The join layer does not merge Offer A and Offer B into a synthetic global
truth object.

## SemanticTopologyNeighborhood

A neighborhood is a projection around one WorkUnit containing:

- all incoming edges;
- all outgoing edges;
- required/optional incoming edge IDs;
- edge-local Demand references;
- producer Offer references when available;
- edge Compatibility references and decisions;
- fan-in/fan-out counts.

Neighborhood identity is derived from graph/edge identities, never list
position or phase number.

## SemanticJoinEvaluation

A join evaluates required incoming edge Compatibility records.

Decision precedence for required edges:

1. any blocked required edge → blocked;
2. otherwise any unresolved/insufficient required edge → insufficient_evidence;
3. otherwise any constrained required edge → admitted_with_constraints;
4. otherwise → admitted.

Optional incoming edges are observed and reported but do not block required
join admission.

## Authority

Before topology aggregation, the service verifies:

- SemanticExecutionGraph authority;
- EdgeSemanticDemand authority;
- SemanticOffer authority;
- OfferDemandCompatibility authority;
- Compatibility references to exact Offer/Demand authority hashes.

Topology projections have their own authority hashes and never mutate their
inputs.

## Epistemic rules

- missing Compatibility is unresolved, not false;
- blocked Compatibility is explicit negative admission evidence;
- optional blocked edges do not become required;
- fan-out consumers remain independent;
- one producer Offer may have different compatibility decisions on different
  outgoing edges;
- graph order and node position have no semantic authority.

## Sprint 7 boundary

Sprint 6 may inspect and aggregate existing topology.

It must not:

- insert/remove/rewrite graph nodes;
- insert/remove/rewrite graph edges;
- revise completed Offers;
- revise frozen Demands;
- rewrite historical Compatibility decisions.

Those operations require the explicit parent-hash/provenance-bound graph
revision contracts reserved for Sprint 7.
