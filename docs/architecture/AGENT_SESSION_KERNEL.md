# Agent Session Kernel

Sprint 1 created a shared session contract for the AIpinho local multi-agent runtime.

## Purpose

The Agent Session Kernel gives AIpinho, Lucio, Codex and Gemini one common way to expose:

- agent profiles;
- independent chat sessions;
- messages;
- runs;
- visible events;
- aggregated session state.

It does not replace the existing chat, Codex or Gemini runtimes. In this sprint it is a compatibility and persistence layer.

## Agents

The registry lives in `config/agents/agent_registry.yaml`.

Initial agents:

- `aipinho`: local orchestrator and principal runtime.
- `lucio`: multimodal strategic orchestrator profile, profile-only in this sprint.
- `codex`: local CLI/code executor profile, adapter over existing Codex Agent session store.
- `gemini`: cloud agent profile, adapter over existing Gemini Executor session store.

No provider secret is stored in the registry.

## Storage

Default storage:

`data/runtime/agent_kernel`

Files:

- `sessions.json`;
- `messages/{agent_id}/{session_id}.jsonl`;
- `runs/{run_id}.json`;
- `events/{run_id}.jsonl`.

The environment variable `AIPINHO_AGENT_KERNEL_ROOT` can redirect the store for tests.

## Public API

Canonical read/write API for agent sessions:

- `GET /api/v1/agents/status`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{agent_id}`
- `GET /api/v1/agents/{agent_id}/sessions`
- `POST /api/v1/agents/{agent_id}/sessions`
- `GET /api/v1/agents/{agent_id}/sessions/{session_id}`
- `PATCH /api/v1/agents/{agent_id}/sessions/{session_id}`
- `DELETE /api/v1/agents/{agent_id}/sessions/{session_id}`
- `GET /api/v1/agents/{agent_id}/sessions/{session_id}/messages`
- `POST /api/v1/agents/{agent_id}/sessions/{session_id}/messages`
- `GET /api/v1/agents/runs/{run_id}`
- `GET /api/v1/agents/runs/{run_id}/events`

## Raw visibility

Normal message APIs return `AgentMessagePublic`.

`raw_ref` is hidden by default and represented only as:

- `raw_available=true/false`.

Raw content is not embedded in normal chat/session responses.

## State precedence

The aggregated state prefers active or unsafe states over older completed runs:

`blocked > failed > validation_failed > pending_approval > pending_validation > applying > running > preview_created > completed > idle`

This keeps a completed simple chat from hiding a pending approval, validation failure or policy block.

## Compatibility

The kernel can read existing sessions from:

- AIpinho chat session store;
- Gemini Executor session store;
- Codex Agent session store.

Compatibility sessions are read-only through this kernel. Deletion by the Agent Kernel soft-deletes only native Agent Kernel sessions.

## Non-goals for Sprint 1

- No tool gateway.
- No delegation execution.
- No memory sharing.
- No auto-cure.
- No UI rewrite.
- No destructive migration of existing session stores.


## Sprint 2 Event Timeline Addendum

The Agent Session Kernel now exposes event-driven timelines through the Multi-Agent Event Bus.

- Events have run-level `sequence` and session-level `session_sequence`.
- Session timeline supports `after_event_id` and `after_sequence`.
- Mobile view-models can poll `/api/v1/mobile/agents/{agent_id}/view-model`.
- Normal mode hides raw references and details mode shows sanitized metadata.
