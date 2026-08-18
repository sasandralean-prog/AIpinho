# Codex Agent Executor

## Status

Sprint 7 turns the existing Codex chat island into a governed technical executor
connected to the multi-agent kernel.

The Codex Agent remains separate from the main AIpinho chat:

- separate sessions;
- separate persisted messages;
- separate runs;
- separate artifacts;
- separate mobile view-model.

It is integrated with the shared governance layer:

- Agent Session Kernel;
- Multi-Agent Event Bus;
- Tool Gateway;
- Policy Kernel and autoapproval;
- Memory Gateway;
- token-protected artifacts.

## Runtime Flow

```text
Codex chat/session
-> CodexAgentService.send
-> CodexRun
-> AgentSessionKernel bridge session/run
-> Codex CLI read-only response
-> optional explicit tool_requests
-> Tool Gateway policy/capability/workspace decision
-> events/artifacts/validation
-> Codex mobile view-model
-> memory candidate best-effort
```

The Codex CLI call is intentionally read-only. Side effects are represented as
explicit tool requests and pass through the Tool Gateway.

## Governed Tool Requests

`CodexAgentRequest.tool_requests[]` is the structured bridge from Codex Agent to
Tool Gateway.

Fields:

- `tool_name`
- `workspace_id`
- `path_ref`
- `operation_type`
- `input`
- `metadata_sanitized`

Supported tools come from `config/agents/tool_gateway_registry.yaml`. Examples:

- `read_file`
- `search_files`
- `create_file`
- `modify_file`
- `patch_preview`
- `patch_apply`
- `run_shell`
- `validate`
- `create_artifact`
- `generate_report`

## Safety Rules

- Codex does not write files directly from chat text.
- Codex does not run free shell.
- Codex does not apply patch outside Tool Gateway.
- Tool policy owns capability/workspace decisions.
- Artifacts use `/api/v1/agents/artifacts/{artifact_id}/download`.
- Tokens are never placed in artifact URLs.
- Memory write is candidate-based and best-effort.

## Storage Roots

Runtime roots are configurable for tests and portable deployments:

- `AIPINHO_CODEX_AGENT_ROOT`
- `AIPINHO_AGENT_KERNEL_ROOT`
- `AIPINHO_TOOL_GATEWAY_ROOT`
- `AIPINHO_AGENT_MEMORY_ROOT`
- `AIPINHO_POLICY_KERNEL_ROOT`
- `AIPINHO_EVENT_STORE_ROOT`
- `AIPINHO_EVENT_RAW_ROOT`
- `AIPINHO_EVENT_AUDIT_ROOT`

## Events

Codex emits Codex-scoped events:

- `codex_run_created`
- `codex_run_started`
- `codex_run_policy_check`
- `codex_auto_approval_granted`
- `codex_run_planning`
- `codex_explanation`
- `codex_tool_requested`
- `codex_tool_succeeded`
- `codex_tool_blocked`
- `codex_tool_approval_required`
- `codex_tool_failed`
- `codex_validation_passed`
- `codex_validation_failed`
- `codex_memory_candidate_created`
- `codex_run_completed`

The Tool Gateway also emits canonical multi-agent events on the bridged kernel
run.

## Acceptance

Sprint 7 is accepted when:

- Codex sessions remain isolated from AIpinho chat.
- Codex run creates an Agent Kernel bridge run.
- Codex tool request reaches Tool Gateway.
- Artifact creation returns token-safe metadata.
- Memory candidate is created without blocking execution.
- Existing multi-agent kernel, policy, delegation, memory and event bus tests
  continue passing.
