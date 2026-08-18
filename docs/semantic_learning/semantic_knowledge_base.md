# Semantic Knowledge Base

The Semantic Knowledge Base stores reusable canonical semantic knowledge produced by the Runtime.

It does not store full prompts, personal data, local paths, workspace details, tokens, secrets, or project-specific decisions.

## Components

- `SemanticKnowledgeBase`
- `SemanticKnowledgeEntry`
- `SemanticPattern`
- `SemanticConcept`
- `SemanticRelationship`
- `SemanticEvidence`
- `SemanticVersion`
- `SemanticKnowledgeRepository`
- `SemanticKnowledgeSerializer`
- `SemanticKnowledgeQuery`

## Entry Fields

Each entry contains:

- id;
- semantic concept;
- identified entities as generic labels;
- canonical intent;
- scope;
- constraints;
- confidence;
- ambiguities found;
- canonical ISR;
- evidence;
- version.

## Endpoints

- `GET /api/v1/runtime/semantic-learning/knowledge`
- `POST /api/v1/runtime/semantic-learning/query`
- `GET /api/v1/runtime/semantic-learning/concepts`

## Safety

The base stores only canonical semantic representations.

Forbidden:

- full prompt text;
- personal data;
- workspace paths;
- local paths;
- tokens;
- secrets.
