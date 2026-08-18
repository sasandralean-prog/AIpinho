# Hotfix P0 - Active Runs / Chat Dispatch Saturation / Session Leak

Generated at: 2026-06-25T02:33:33.882725+00:00

## Verdict

**ACTIVE_RUN_DISPATCH_HOTFIX_READY**

## Preflight

- Total runs: 215
- Effective active runs before cleanup: 19
- Stale active runs before cleanup: 19
- Total sessions: 213
- Active sessions before cleanup: 196
- Stale sessions over 24h: 196

Evidence: `reports/hotfix_active_runs_dispatch_saturation_preflight.md` and `.json`.

## Root Cause

The multi-agent dashboard counted old runs as active because stored run status and event precedence could leave a run in `created` or `running` even when the run had `completed_at` or no recent progress. Old sessions were also left unarchived, so the active session count kept growing. Chat send paths persisted user messages, but if dispatch/response failed afterwards the user could see silence instead of a visible assistant error.

## Fixes Applied

1. Runtime hygiene now detects stale runs using effective status, last event, `started_at`, `completed_at`, and creation-only runs.
2. Run cleanup marks stale runs as `cancelled`, keeps evidence, and emits `run_marked_stale` plus `run_slot_released`.
3. Session cleanup archives inactive sessions without deleting history.
4. Queue health endpoint added at `/api/v1/runtime/hygiene/queue-health` with active/queued/stale runs, pending approvals, active sessions, dispatcher status, capacity and available slots.
5. Dashboard effective status now treats `completed_at` and terminal events as terminal, avoiding active run ghosts.
6. Persistent chat send now creates a visible assistant degraded/error message if dispatch is saturated or response creation fails after the user message is stored.
7. Workspace registry permission status routing now recognizes configurable registry/configured terms.
8. Workspace role contract resolver filters extra config fields before strict schema construction, allowing richer registry config without ValidationError.

## Cleanup Executed

- Preview id: `cleanup_preview_f997172ab8fd4366bf2bd2f25ba15863`
- Candidates: 204
- Applied: 204
- Deletes evidence: false
- Queue health after cleanup: `{"status": "ok", "active_runs": 0, "queued_runs": 0, "stale_runs": 0, "pending_approvals": 0, "active_sessions": 0, "dispatcher_status": "available", "worker_pool_capacity": 8, "worker_pool_available_slots": 8, "stale_run_ids": [], "backpressure_required": false, "reason_code": null}`

## Files Changed

- `src/aipinho/services/runtime/runtime_state_hygiene_service.py`
- `src/aipinho/services/agents/multi_agent_observability_service.py`
- `src/aipinho/api/routers/runtime_hygiene_router.py`
- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/services/policy_kernel/workspace_role_contract_service.py`
- `config/chat/chat_operation_routing_policy.yaml`
- `tests/unit/test_runtime_state_hygiene_service.py`
- `tests/integration/test_chat_runtime_parity_api.py`
- `tests/unit/test_chat_operation_router_service.py`

## Tests / Commands

- `python -m py_compile <altered python files>`
- `pytest tests/unit/test_runtime_state_hygiene_service.py -q -> 15 passed`
- `pytest tests/integration/test_chat_runtime_parity_api.py -q -k "saturation or no_silent" -> 2 passed`
- `pytest tests/unit/test_chat_operation_router_service.py -q -k "permission_status or registered_workspace" -> 5 passed`
- `pytest tests/unit/test_workspace_permission_matrix_service.py tests/unit/test_operational_trust_kernel.py -q -> 13 passed`
- `runtime hygiene preview/apply max_age_hours=1 kinds=run,session,delegation -> 204 applied`
- `restart backend 9088 via scripts/dev/stop_aipinho_9088.ps1 and start_aipinho_9088.ps1`
- `HTTP smoke /health, /runtime/hygiene/queue-health, persistent chat sends`

## Smoke Results

- `/api/v1/health`: `ok`
- `/api/v1/runtime/hygiene/queue-health`: `available`, slots `8/8`
- Mobile Chat smoke: status `ok`, operation `conversation`, assistant_created `True`
- Launcher Chat smoke: status `ok`, operation `conversation`, assistant_created `True`
- Workspace registry smoke: status `ok`, operation `permission_status`, assistant_created `True`

## Residual Risks / Backlog

- Full `test_chat_runtime_parity_api.py` still has unrelated pre-existing parity failures for sandbox batch and forbidden root when run without filter. They were not introduced by this hotfix and need a separate parity/router policy pass.
- The chunk assembly protocol is not fully formalized in `ChatMessageCreateRequest`; this hotfix prevents silent chat failure/backpressure, but a future sprint should define explicit chunk ids, chunk timeout storage, and assembly semantics.

## Final

The active run/session saturation condition was reconciled and the backend now reports available executor slots. Mobile/Launcher equivalent persistent chat sends produce assistant messages again, and status/permission queries no longer fail silently.
