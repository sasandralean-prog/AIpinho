# Sprint I Preflight

Status: READY

Existing pieces found:

- Gemini Executor exists as an older provider-specific island.
- External workspace registry exists, but it is unrelated to external model collaboration.
- No provider-neutral external collaboration contract layer existed before this sprint.
- Sprint H Universal Task Session exists and is the correct progress source for external clients.

Design decision:

- Implement a provider-neutral `/api/v1/external` collaboration boundary.
- Keep Gemini as an adapter registered behind `/external/adapters/{adapter_id}/review`.
- Do not grant runtime, task store, validation, approval or execution authority to external providers.

