# Bloco C - Residual Legacy Migration + Quarantine Completion + Controlled Deletion

Status final: GOVERNANCE_BLOCK_C_LEGACY_DELETION_READY

Generated UTC: 2026-06-26T10:32:19.629848+00:00

## Checkpoints

- G14_RESIDUAL_ENDPOINT_OWNERSHIP_MAP_READY
- G15_RESIDUAL_ENDPOINT_MIGRATION_READY
- G16_LEGACY_CHAT_SERVICES_FOLDED_READY
- G17_LEGACY_QUARANTINE_COMPLETED_READY
- G18_LEGACY_DELETION_PREFLIGHT_READY
- G19_LEGACY_DELETION_REGRESSION_READY

## Endpoints migrated

- Chat direct/preview/approval command/session/timeline/raw/copy/feedback.
- OpenAI-compatible `/v1/models` and `/v1/chat/completions`.
- Continue compatibility `/v1/integrations/continue/chat`.
- VSCode Continue action preview/execute.
- Chat status/diagnostics/model-status/manual-inference.

## Files quarantined

- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/api/routers/continue_integration_router.py`

## Files deleted

- `config/runtime/runtime_profiles.yaml` from quarantine.

## Files retained and why

- `ChatService`: retained as content provider for plain conversation after canonical lifecycle decision.
- `ChatOperationRouterService`: retained because `ChatService` still imports it internally; it no longer owns public route operation lifecycle.
- `ChatPermissionGrantService`: retained because grant storage semantics still exist internally; public readonly/planning and migrated routes no longer delegate final permission authority to it.

## Canonical configs active

- `config/governance/lifecycle.yaml`
- `config/governance/intents.yaml`
- `config/governance/policy.yaml`
- `config/governance/approval.yaml`
- `config/governance/runtime_profiles.yaml`
- `config/governance/completion_policy.yaml`

## Tests executed

```text
python -m py_compile src/aipinho/api/routers/governance_lifecycle_router.py src/aipinho/api/routers/__init__.py
python -m pytest tests/governance/... focused + selected chat integration tests -q
35 passed in 84.18s
```

## Risks remaining

- P1: `ChatService` still contains internal legacy routing helpers for content-provider fallback. Public routes do not use it for final lifecycle authority, but a later cleanup can split a pure content provider.
- P2: Historical reports and a certification test name still mention `chat_router.py`.

## Recommended next gate

Bloco D - G20 Multichannel Governance Firetest.

Expected gate: GOVERNANCE_UNIFIED_SYSTEM_READY.

