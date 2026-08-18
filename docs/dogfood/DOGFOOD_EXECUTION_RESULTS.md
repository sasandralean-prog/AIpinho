# Dogfood Execution Results

## Main Run

- Agent: `aipinho`
- Session: `agent_session_1c34fc646df341098623d881245afb18`
- Run: `agent_run_d45f4538979b49279ccfad547e310a83`
- Final status: `completed`
- Validation status: `passed`

## Governed Actions

- Source listing: succeeded.
- Source file reads: succeeded.
- Source write negative test: blocked with `source_readonly_write_denied`.
- Target patch preview: succeeded.
- Target file creation: succeeded.
- Governed shell validation: succeeded.
- Final validation: passed.
- Report artifact: created.

## Artifact

- Artifact id: `agent_artifact_b61c62dc419d4b1f9ea2192cc39b67a8`
- Filename: `sprint20_dogfood_report.md`
- Download endpoint: `/api/v1/agents/artifacts/agent_artifact_b61c62dc419d4b1f9ea2192cc39b67a8/download`
- Requires token: true.

## Validation

Target command:

```text
python -m pytest -q
```

Result:

```text
3 passed in 0.04s
```

## Mobile/Endpoint State

After the Sprint 20 state fix and backend restart:

- `latest_status`: `completed`
- `active_run_present`: false
- `safety_label`: `safe`
- `validation_status`: `passed`
- artifact count present in mobile view-model.

