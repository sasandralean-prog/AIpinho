# Artifact Index

The index path is configured by `config/artifacts/artifact_library_policy.yaml`.

Default:

`C:\Dev\AIpinho\artifacts\ARTIFACT_INDEX.json`

The index is rebuilt from authoritative stores:

- `data/runtime/agent_tool_gateway/artifacts.json`
- `data/artifacts/manifests/artifact_registry.json`

Reindexing is safe and non-destructive. It marks missing ready files as failed instead of pretending they are downloadable.
