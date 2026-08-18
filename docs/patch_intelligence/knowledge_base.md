# Patch Intelligence Knowledge Base

The Patch Intelligence Knowledge Base stores generic correction knowledge for runtime regressions.

It does not store patch code, diffs, project-specific rules, or absolute paths.

## Components

- `PatchKnowledgeBase`
- `PatchKnowledgeEntry`
- `PatchPattern`
- `PatchCategory`
- `PatchHistory`
- `PatchEvidence`
- `PatchRelationship`
- `PatchKnowledgeSerializer`
- `PatchKnowledgeRepository`
- `PatchKnowledgeQueryService`

## Entry Fields

Each entry contains:

- unique id;
- category;
- associated regression;
- root cause;
- correction strategy;
- affected modules;
- affected files as generic module paths only;
- related tests;
- related Fire Tests;
- evidence;
- confidence;
- risk;
- date;
- runtime version.

## Safety Rules

- no project-specific patches;
- no absolute paths;
- no code patches;
- no automatic application;
- deterministic query behavior.

## Endpoints

- `GET /api/v1/runtime/patch-intelligence/knowledge`
- `GET /api/v1/runtime/patch-intelligence/knowledge/{id}`
- `POST /api/v1/runtime/patch-intelligence/query`
