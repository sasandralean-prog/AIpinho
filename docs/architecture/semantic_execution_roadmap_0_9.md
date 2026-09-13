# Semantic Execution Roadmap — Sprints 0–9

## Architectural invariants

The sprint sequence is cumulative. Later sprints must extend earlier contracts
rather than bypass or replace their authority boundaries.

- MODEL != AUTHORITY.
- Phase identifiers are operational identifiers, not semantic authority.
- TaskSemanticVocabulary is frozen and hash-bound before semantic execution.
- A downstream demand never determines an upstream result.
- An upstream outcome never authorizes a downstream consumer by status alone.
- Compatibility belongs to a producer→consumer edge.
- Past canonical truth is immutable.
- Unknown remains fail-closed.
- Graph/vocabulary revisions are explicit, additive where possible, versioned,
  and provenance-bound.
- FireTests provide real-world evidence; they are not runtime configuration.

## Sprint sequence

### Sprint 0 — Hybrid semantic dependency foundation

Establish candidate-only model reasoning, deterministic gates, limitation
reasoning, generic playbook semantics, and fail-closed dependency evaluation.

### Sprint 1 — Typed Task Semantic Vocabulary

Establish the canonical ontology shared by the whole TaskRun:

- system and task-local typed concepts;
- allowed-state and requirement-state domains;
- typed identity as (concept_type, concept_id);
- provenance;
- deterministic compilation;
- freeze/hash authority;
- additive revision with explicit parent binding;
- TaskRunPlan binding;
- semantic demand/playbook binding to the frozen vocabulary.

### Sprint 2 — Semantic Work Units and Semantic Execution Graph

Replace phase-number semantics with task-derived work units and typed graph
structure. Every work unit and edge references the same frozen vocabulary
binding. Forward decomposition must be generic and graph topology must not
assume a linear chain.

### Sprint 3 — Edge-local Semantic Demand

Compile consumer requirements onto producer→consumer edges. Demand describes
what the consumer needs and must be frozen independently of observed producer
outcomes.

### Sprint 4 — Producer Semantic Offer

Synthesize evidence-backed semantic offers from executed work units:
observed/inferred/derived/unknown properties, use-safety, limitations and
evidence bindings. Producer truth remains local and immutable.

### Sprint 5 — Generic Offer/Demand Compatibility

Evaluate SemanticOffer against SemanticDemand per edge. The same offer may be
admitted for one consumer, constrained for another and blocked for a third.

### Sprint 6 — N-1 / N / N+1 and non-linear dependencies

Support fan-in, fan-out, multi-producer joins, combined incoming constraints
and outgoing demand forecasts without assuming a single predecessor or
successor.

### Sprint 7 — Governed graph revision

Support explicit graph revisions when execution discovers new work. Revisions
bind to parent graph/vocabulary hashes and preserve completed historical
outcomes.

### Sprint 8 — Completion, SpeakerTruth and Doctor

Project graph state, semantic offers, compatibility and evidence into
user-facing operational truth. Observability diagnoses canonical state but
does not grant authority.

### Sprint 9 — Anti-FireTest generalization

Prove the architecture across unrelated domains and topologies. FireTest 5
becomes one regression among many rather than the architecture's implicit
workflow.

## Cross-sprint authority chain

```text
Prompt / Intent
    ↓
TaskSemanticVocabulary          [Sprint 1]
    ↓
SemanticExecutionGraph          [Sprint 2]
    ↓
Edge SemanticDemand             [Sprint 3]
    ↓
Governed WorkUnit Execution
    ↓
SemanticOffer                   [Sprint 4]
    ↓
Offer/Demand Compatibility      [Sprint 5]
    ↓
N-way Graph Semantics           [Sprint 6]
    ↓
Explicit Graph Revision         [Sprint 7]
    ↓
SpeakerTruth / Doctor           [Sprint 8]
    ↓
Cross-domain Generalization     [Sprint 9]
```

Sprint 0 remains the deterministic/model-governance foundation under every
stage above.
