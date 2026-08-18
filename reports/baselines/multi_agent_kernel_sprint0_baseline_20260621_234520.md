# Multi-Agent Kernel Sprint 0 Revalidation

Generated: 2026-06-21T23:45:20-03:00
Mode: read-only inventory and documentation revalidation

## Executive Summary

The current AIpinho runtime already contains the Sprint 0 baseline artifacts and the later multi-agent foundation. This revalidation did not add a second kernel or alter production behavior under Sprint 0 scope. The model-assisted patch planner recorded separately in `reports/fixes/model_assisted_patch_planning_20260621_234520.md` was completed before this audit at the user's request.

## Runtime Overview

- FastAPI app factory: `src/aipinho/app_factory.py`.
- Router registry: `src/aipinho/api/routers/__init__.py`.
- Current inventory: 117 router modules, 1080 service modules, 853 schema modules, and 776 Python test files.
- Official API namespace: `/api/v1`.
- Core domains: chat, task runtime, policy kernel, governed tools, approvals, patch planning/apply, validation, artifacts, model/role inference, events/debugger, memory/RAG, agent kernel, Gemini, Codex, and Lucio.

## Current Chat and Session Model

- AIpinho chat remains at `/api/v1/chat` with persistent sessions, messages, timelines, sanitized copy, raw-on-demand, and artifacts.
- Agent session compatibility is provided by `AgentSessionKernelService`; AIpinho, Lucio, Codex, and Gemini use isolated `agent_id` and `session_id` namespaces.
- The primary chat remains compatible rather than being destructively migrated.

## Current Task, Approval, and Tool Model

- `TaskRuntimeService`, `SupervisedExecutionLoop`, `TaskRunGuard`, and runtime profiles own task execution state.
- Patch previews are created by `PatchPlanningService`; apply is guarded by the quality gate and `PatchApplyApprovalBridge`.
- `GovernedToolExecutionService` and workspace policies own filesystem and shell boundaries.
- Artifact output has an independent lifecycle and is not treated as an implicit workspace write.

## Events, Debugger, and Persistence

- Native agent kernel persistence: `data/runtime/agent_kernel` using `sessions.json`, JSONL messages, JSON runs, and JSONL events.
- Agent events have per-run and per-session sequencing. Normal presentation hides raw references.
- Debugger, event, and realtime domains remain separate from the chat response surface.

## Mobile and Launcher

- Mobile source includes agent/session repositories, agent API client, chat aggregation, pipeline, debugger, artifacts, and humanized renderers.
- Launcher and desktop artifacts are present under `apps/launcher`; its exact UI composition remains a separate visual QA concern.

## Fire Test 3 Baseline

- Historical reports exist under `reports/fire_tests`, `reports/aipinho_firetest3_*`, and `reports/fire_tests/aipinho_firetest_pinhoforge_studio2_*`.
- Current recorded closure is `AIPINHO_FIRETEST_PINHOFORGE_READY`, while historical visual/legacy-test caveats remain explicitly documented in their reports.

## Reuse Map

| Need | Current owner | Reuse decision |
| --- | --- | --- |
| Agent identity and session state | `AgentSessionKernelService` | Reuse directly |
| Events/timeline | `MultiAgentEventBus` + timeline mapper | Reuse directly |
| Delegation contracts | `AgentDelegationService` | Reuse through policy, do not create parallel calls |
| Tools and policy | Tool Gateway / Policy Kernel | Reuse only |
| Task execution | `TaskRuntimeService` | Keep as execution owner |
| Artifacts | Artifact services | Reuse lifecycle and token policy |
| Patch previews | `PatchPlanningService` | Reuse; model adapter is preview-only |

## Main Risks

1. Router and service breadth can hide duplicate paths; new features must compose existing owners.
2. Historical compatibility adapters must not mix agent timelines or raw content.
3. Patch planning is now model-assisted but apply remains intentionally separate and must retain quality/approval checks.
4. Legacy RAG needs continued isolation from ordinary chat and agent-state contexts.
5. UI needs cross-surface QA whenever new agent state is added.

## Sprint 1 Plan and Current Status

The Sprint 1 Agent Session Kernel was already delivered historically and remains present. Revalidation should run the kernel unit/API tests, verify the four registry profiles, preserve compatibility readers, and avoid destructive migration. No Sprint 2 work is started by this report.
