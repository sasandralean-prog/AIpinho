
# G11 Canonical Routes and Endpoints Report

- Generated UTC: 2026-06-26T09:13:16.008830+00:00
- Mode: real public route ownership replacement for critical operational endpoints.
- Checkpoint: `G11_CANONICAL_ROUTES_ENDPOINTS_READY`

## What changed

A new canonical public router was created and mounted before legacy chat/continue routers:

- `src/aipinho/api/routers/governance_lifecycle_router.py`

The router now owns the first matching route for:

- `POST /api/v1/chat`
- `POST /api/v1/chat/preview`
- `POST /api/v1/chat/approval-command`
- `POST /api/v1/chat/sessions/{session_id}/send`
- `GET /v1/models`
- `GET /v1/models/{model_id}`
- `POST /v1/chat/completions`
- `POST /v1/integrations/continue/chat`

The router registry was updated:

- `src/aipinho/api/routers/__init__.py`

A new public service owns canonical public response finalization:

- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`

The public response schema now exposes:

- `governance_lifecycle`

## What this means

The public operational endpoints above are no longer first served by the legacy chat or Continue routers. They are served by `governance_lifecycle_router` first. Existing domain services can still provide content/previews/artifacts internally, but public operational truth is attached through `GovernanceLifecycleSnapshot`.

## Legacy status

Legacy routers are still mounted for residual endpoints and compatibility. They were not moved to quarantine in G11 because quarantine is the G13 step. The G11 tests prove first-route ownership for critical public operational endpoints.

## Tests

Executed:

- `python -m py_compile src\aipinho\api\routers\governance_lifecycle_router.py src\aipinho\api\routers\__init__.py src\aipinho\services\governance\lifecycle\canonical_public_chat_service.py src\aipinho\services\governance\lifecycle\public_route_lifecycle_service.py src\aipinho\schemas\chat\chat_response.py`
- `python -m pytest tests\governance\test_g11_canonical_public_routes.py -q` -> 5 passed
- `python -m pytest tests\governance\test_lifecycle_core.py tests\governance\test_g11_canonical_public_routes.py tests\integration\test_chat_api.py::test_post_chat_greeting_200 tests\integration\test_chat_api.py::test_chat_status_200 tests\integration\test_chat_runtime_parity_api.py::test_no_silent_message_after_persistent_chat_send -q` -> 14 passed

## Regressions added

- Direct chat returns `governance_lifecycle`.
- Persistent chat send returns `governance_lifecycle` inside `chat_response`.
- Continue/OpenAI-compatible response returns canonical lifecycle metadata.
- Route order proves canonical router owns public operational endpoints first.

## Checkpoint

`G11_CANONICAL_ROUTES_ENDPOINTS_READY`
