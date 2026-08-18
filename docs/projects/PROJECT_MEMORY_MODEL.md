# Project Memory Model

Project Profile integration scopes memory and artifacts by project.

Namespaces:

- `memory:project:{project_id}`
- `artifacts:projects:{project_id}`
- `reports:projects:{project_id}`

Rules:

- Project memory is curated, not raw RAG.
- Raw logs are not memory.
- Secret-bearing content is blocked.
- Tool artifacts can create memory candidates only with sanitized metadata and evidence refs.
- Profile context is evidence, not final truth.

