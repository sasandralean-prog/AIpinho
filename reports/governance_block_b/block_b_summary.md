
# Governance Block B Summary

- Generated UTC: 2026-06-26T09:13:16.008830+00:00
- Status: `GOVERNANCE_BLOCK_B_CANONICAL_REWIRE_REQUIRES_PATCH`
- Superseded by: `reports/governance_block_b/block_b_final_summary.md`

## Completed checkpoints

- `G6_CANONICAL_LIFECYCLE_CORE_READY`
- `G7_CANONICAL_INTENT_ROUTER_READY`
- `G8_CANONICAL_POLICY_PERMISSION_READY`
- `G9_CANONICAL_PREVIEW_APPROVAL_READY`
- `G10_CANONICAL_RUNTIME_COMPLETION_READY`
- `G11_CANONICAL_ROUTES_ENDPOINTS_READY`
- `G12_FULL_RECHECK_READY_WITH_RESIDUAL_LEGACY`
- `G13_LEGACY_QUARANTINE_READY_PARTIAL`

## Core files created or changed

- `src/aipinho/schemas/governance/lifecycle.py`
- `src/aipinho/schemas/chat/chat_response.py`
- `src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py`
- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`
- `src/aipinho/services/governance/intent/canonical_intent_router.py`
- `src/aipinho/services/governance/intent/intent_normalizer.py`
- `src/aipinho/services/governance/intent/intent_decision.py`
- `src/aipinho/services/governance/policy/canonical_policy_service.py`
- `src/aipinho/services/governance/approval/canonical_approval_service.py`
- `src/aipinho/services/governance/runtime/canonical_runtime_service.py`
- `src/aipinho/services/governance/completion/completion_resolver.py`
- `src/aipinho/services/governance/speaker_truth/speaker_truth_service.py`
- `src/aipinho/api/routers/governance_lifecycle_router.py`
- `src/aipinho/api/routers/__init__.py`
- `config/governance/lifecycle.yaml`
- `config/governance/intents.yaml`
- `config/governance/policy.yaml`
- `config/governance/approval.yaml`
- `config/governance/runtime_profiles.yaml`
- `config/governance/completion_policy.yaml`
- `tests/governance/test_lifecycle_core.py`
- `tests/governance/test_g11_canonical_public_routes.py`
- `tests/governance/test_g7_functional_route_rewire.py`
- `tests/governance/test_g12_full_recheck.py`
- `tests/governance/test_canonical_lifecycle_trace.py`
- `tests/governance/test_no_legacy_operational_bypass.py`
- `tests/governance/test_legacy_import_forbidden.py`

## Public routes replaced first

- `POST /api/v1/chat`
- `POST /api/v1/chat/preview`
- `POST /api/v1/chat/approval-command`
- `POST /api/v1/chat/sessions/{session_id}/send`
- `POST /v1/chat/completions`
- `POST /v1/integrations/continue/chat`

## Tests executed

- `python -m py_compile ...` passed.
- `python -m pytest tests\governance\test_lifecycle_core.py -q` -> 7 passed.
- `python -m pytest tests\governance\test_g11_canonical_public_routes.py -q` -> 5 passed.
- Combined focused set -> 25 passed.

## Remaining work

- Expand canonical route replacement to residual endpoints still owned by `chat_router.py` and `continue_integration_router.py`.
- Fold remaining legacy chat operation/grant services into canonical signal providers before moving them to quarantine.

## Honest limitation

The canonical public router now owns the critical operational routes first. One stale runtime config was quarantined, but legacy routers remain mounted for residual endpoints. This is not full legacy quarantine yet.
