# Governed Write Flow

## Purpose

The main AIpinho chat may execute explicit low/medium-risk file writes only through the governed Tool Gateway.

## Flow

User prompt
-> ChatOperationRouter
-> governed_file_write
-> GovernedWriteRequest
-> GovernedWriteChatService
-> Agent Tool Gateway
-> Workspace resolver
-> Policy Kernel
-> auto approval or approval
-> create_file/modify_file
-> validation result
-> ChatResponse with evidence_refs

## Invariants

- Simple conversation never writes.
- Missing workspace returns `needs_clarification`.
- source_readonly/protected/forbidden writes are blocked.
- target_mutable writes must go through Tool Gateway.
- The chat does not bypass policy, approval, validation or event trace.
- Evidence refs include the agent run and tool invocation.

## Current RC2 Support

- `governed_file_write` handles explicit create-file prompts with a real filename.
- `GovernedWriteRequest` is the normalized contract for chat-to-tool writes.
- `AgentLocalActionPlanner` extracts filename/content and delegates execution to `AgentToolGatewayService`.

## Non-Goals

- No free shell.
- No destructive writes.
- No write into source_readonly.
- No special handling for project names, sprint names or hardcoded paths.
