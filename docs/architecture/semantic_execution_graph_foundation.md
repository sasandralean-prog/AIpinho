# Semantic Execution Graph Foundation

## Status

Sprint 2 canonical foundation for semantic work decomposition.

This layer extends Sprint 0 deterministic/model governance and Sprint 1
TaskSemanticVocabulary. It does not replace either authority boundary.

## Separation of concerns

SemanticExecutionGraph is not the operational ExecutionGraph.

SemanticExecutionGraph describes:

- semantic work units;
- the canonical source steps represented by each work unit;
- governed work modes;
- capabilities and effects;
- explicit semantic/dependency relations;
- frozen vocabulary binding;
- graph authority hash.

The operational ExecutionGraph remains responsible for workers, scheduling,
runtime status, retries and execution mechanics.

Operational ordering is not semantic dependency authority.

## Work-unit invariants

A SemanticWorkUnitContract:

- derives identity from TaskRun, vocabulary authority and source_step_ids;
- never derives semantic identity from phase number or list position;
- references a frozen TaskSemanticVocabulary binding;
- preserves canonical source capabilities;
- may represent one or more canonical execution steps;
- distinguishes explicit/interpreted/unknown classification.

Unknown work mode is represented explicitly as unknown. It is not inferred
from action names, filenames, deliverables or step position.

## Structural graph

The deterministic structural compiler provides a truthful minimum graph before
model interpretation.

It:

- covers every canonical execution step;
- creates no implicit linear edges;
- preserves explicit canonical depends_on relations;
- validates governed capabilities, work modes and effects;
- produces a partial graph when semantic classification is unavailable;
- fails closed on invalid authority, unknown dependencies or cycles.

A partial graph means valid structure with incomplete semantic classification.
It is not equivalent to semantic admission for a downstream consumer.

## Model-assisted decomposition

The model may propose:

- grouping of canonical steps into semantic work units;
- governed work modes;
- governed effects;
- semantic edge relations.

The deterministic gate requires:

- exact source-step coverage;
- no invented, omitted or duplicated steps;
- exact canonical capability union per unit;
- governed work modes/effects only;
- preservation of explicit dependencies;
- valid edge endpoints;
- no self edge;
- acyclic topology;
- sufficient confidence and rationale.

The model never assigns canonical IDs or authority hashes.

## FireTest evidence

FireTest inputs are validation evidence, not runtime configuration.

Sprint 2 compile-only validation against the historical FireTest 5 Phase 1
TaskRun produced a valid partial structural graph with eight work units and no
invented edges. Real-model decomposition attempts were fail-closed when model
output was not valid contract JSON.

No production Sprint 2 rule contains FireTest, phase-number, music-domain or
corpus-specific identifiers.

## Sprint 3 handoff

Sprint 3 introduces edge-local SemanticDemand.

SemanticDemand must be a separate canonical contract referencing an existing
SemanticDependencyEdge by edge_id. It must not mutate Sprint 2 graph identity
or rewrite producer work-unit semantics.

The intended authority chain is:

```text
SemanticExecutionGraph (Sprint 2)
    |
    +-- SemanticDependencyEdge
            |
            +-- SemanticDemand (Sprint 3, separate contract)
                    |
                    +-- consumer-local requirements
```

This preserves:

- graph identity independent of downstream requirements;
- producer truth independent of consumer need;
- different demands for different consumers of the same producer;
- future SemanticOffer independence in Sprint 4;
- edge-local Offer/Demand compatibility in Sprint 5.

Sprint 3 must fail closed when graph authority, edge identity or vocabulary
binding cannot be verified.
