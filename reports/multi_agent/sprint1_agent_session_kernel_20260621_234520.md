# Sprint 1 Agent Session Kernel Revalidation

Generated: 2026-06-21T23:45:20-03:00

## Verdict

`approved_revalidated`

## Existing Implementation Confirmed

- Declarative profiles: `config/agents/agent_registry.yaml` contains `aipinho`, `lucio`, `codex`, and `gemini`.
- Common contracts: `AgentProfile`, `AgentSession`, `AgentMessage`, `AgentRun`, `AgentEvent`, and `AgentSessionState` in `schemas/agents/contracts.py`.
- Persistence: `AgentSessionStore` persists native kernel sessions, messages, runs, and events without destructive migration.
- Service: `AgentSessionKernelService` keeps native state separate by `agent_id` and offers compatibility readers for existing AIpinho, Codex, and Gemini histories.
- Events: `MultiAgentEventBus` adds monotonic run and session sequences while preserving hidden/raw boundaries.
- API: `/api/v1/agents` and `/api/v1/mobile/agents` expose the required session, message, run, event, timeline, and mobile-view contracts.

## State Contract

The implementation retains the required precedence so a simple chat cannot conceal an operational state:

`blocked > failed > validation_failed > pending_approval > pending_validation > applying > running > preview_created > completed > idle`

## Security and Compatibility

- Normal-mode messages expose sanitized content and `raw_available`, not `raw_ref`.
- Session isolation is keyed by both agent and session identifiers.
- Native deletion is soft-delete; compatibility stores are not destructively migrated or deleted.
- The legacy `/api/v1/chat/status` contract remains separately available.

## Validation Planned/Executed in This Revalidation

Focused kernel tests are listed in `tests/unit/test_agent_session_kernel_service.py` and `tests/integration/test_agent_event_timeline_api.py`. They cover four profiles, session isolation, raw hiding, event sequencing, state precedence, mobile view models, and chat compatibility.

Executed validation:

```text
python -m pytest tests\\unit\\test_model_assisted_patch_planner_service.py tests\\unit\\test_task_run_executor.py tests\\unit\\test_agent_session_kernel_service.py tests\\integration\\test_agent_event_timeline_api.py -q --durations=10
```

Result: `18 passed in 22.27s`. No real model was invoked by this suite.

## Explicit Non-Goals

No new Tool Gateway, delegation behavior, memory gateway, UI rewrite, provider integration, or agent-specific execution path is introduced by this Sprint 1 revalidation. Those mechanisms already exist from later historical sprints and remain outside this scope.

## Sprint 2 Recommendation Only

If separately authorized, the next work should consume the existing incremental Agent Event Bus in each UI surface and close cross-surface timeline QA. This report does not start Sprint 2.
