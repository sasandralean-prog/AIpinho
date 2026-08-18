# Governed Retrieval Lifecycle

Sprint 25 introduces a read-only retrieval layer. It does not create a vectorstore and it does not grant authority to execute, write, patch or invent missing facts.

## Flow

1. Validate the explicit source selection.
2. Normalize and validate the query.
3. Validate scope and workspace boundaries.
4. Resolve the registered read-only adapter.
5. Retrieve bounded excerpts from the official store or sandbox.
6. block secret, raw-log and sensitive content.
7. Deduplicate and rank deterministically.
8. Apply per-source and total budgets.
9. Build source references and citations.
10. Build an evidence bundle.
11. Mark the context safe for prompt assembly only when every retained hit is cited.
12. Save a sanitized retrieval audit and optional trace.

## Allowed Sources

- `project_files`
- `project_reports`
- `task_results`
- `validation_results`
- `patch_apply_results`
- `curated_memory` when explicitly requested

## Disabled

- Vectorstore creation.
- Embedding generation.
- Automatic ingestion.
- Legacy vectorstore access.
- Network or web retrieval.
- Raw-log retrieval.
- Secret retrieval.
- Automatic chat retrieval.
- Automatic prompt injection.
- Workspace or memory mutation.

Retrieval returns `found`, `partial`, `no_results`, `blocked`, `degraded` or `invalid`. A missing source, invalid scope, forbidden workspace or uncited hit cannot become prompt context.
