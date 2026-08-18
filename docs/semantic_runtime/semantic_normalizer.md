# Semantic Normalizer

Sprint SR4 adds a deterministic Semantic Normalizer.

The normalizer receives an `IntermediateSemanticRepresentation` and returns a
new normalized ISR. It does not read the raw prompt, does not call an LLM, does
not create contracts, and does not touch Runtime execution.

## Components

- `SemanticNormalizer`
- `SynonymResolver`
- `CanonicalIntentResolver`
- `CanonicalScopeResolver`
- `CanonicalConstraintResolver`
- `CanonicalOutputResolver`

## Configuration

Rules live in:

`config/semantic_runtime/semantic_normalizer.yaml`

The config maps synonyms and semantically equivalent forms to canonical values.
For example:

- `corrigir`, `ajustar`, `editar` -> `write_patch`
- `analisar`, `inspecionar`, `auditar` -> `repository_analysis`

## Idempotence

Normalizing an already-normalized ISR must not change the canonical fields.

## Boundary

SR4 does not replace downstream Runtime behavior. It only provides the canonical
semantic normalization layer for future sprints.
