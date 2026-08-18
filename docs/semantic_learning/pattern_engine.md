# Semantic Pattern Engine

The Semantic Pattern Engine recognizes recurring interpretation patterns from canonical semantic structures.

It does not alter the Semantic Interpreter and does not use literal prompt text.

## Components

- `SemanticPatternEngine`
- `SemanticPatternRepository`
- `SemanticPatternScorer`
- `SemanticPatternNormalizer`
- `SemanticPatternValidator`

## Inputs

- ISR
- Semantic Knowledge Base
- Runtime Doctor Report
- Regression Matrix

## Output

`SemanticPatternMatch` containing:

- pattern id;
- concept;
- frequency;
- confidence;
- examples;
- ambiguities;
- relationships.

## Matching Basis

The engine uses:

- canonical intent;
- scope;
- generic entities;
- constraints;
- expected outputs;
- ISR confidence and ambiguity;
- Runtime Doctor structured categories when provided.

It does not use:

- prompt literals;
- project-specific paths;
- workspace-specific details;
- automatic runtime changes.

## Endpoints

- `GET /api/v1/runtime/semantic-learning/patterns`
- `POST /api/v1/runtime/semantic-learning/patterns`
