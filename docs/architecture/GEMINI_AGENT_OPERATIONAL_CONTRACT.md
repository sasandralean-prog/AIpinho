# Gemini Agent Operational Contract

## Identity

- `agent_id`: `gemini`
- provider: `gemini`
- role: cloud agent
- default execution mode: `governed_autorun`
- private memory namespace: `memory:gemini`

## Direct Response Contract

A request may be answered directly only when it does not require local
filesystem, workspace, shell, build, validation or artifact execution.

Completion requires:

- provider response completed;
- parent run completed;
- assistant message persisted;
- run evidence reference present.

## Delegation Contract

A request requiring local capabilities must:

1. create a parent Gemini run;
2. load governed memory context;
3. pass Gemini policy;
4. create a `DelegationRequest` to AIpinho;
5. propagate workspace, capabilities and execution mode;
6. expose delegation and child run references;
7. avoid declaring execution success before child evidence exists.

Approval-required delegations map to parent status `pending_approval`.

## Configuration

The operational switches are external:

- `GEMINI_AGENT_USE_MEMORY_GATEWAY`
- `GEMINI_AGENT_USE_DELEGATION`
- `GEMINI_AGENT_PREFER_AIPINHO_EXECUTOR`
- `GEMINI_AGENT_ALLOW_DIRECT_LOCAL_TOOLS`
- `GEMINI_AGENT_AUTORUN_ENABLED`
- `GEMINI_AGENT_AUTOREVIEW_ENABLED`
- `GEMINI_AGENT_AUTOAPPROVAL_ENABLED`
- `GEMINI_AGENT_RAW_DEFAULT_VISIBLE`
- `GEMINI_AGENT_CLOUD_WARNING_VISIBLE`

Legacy `GEMINI_EXECUTOR_*` variables remain compatible.

## Failure Semantics

- provider failure: `failed`, controlled human error;
- policy denial: `blocked`;
- delegation unavailable: `blocked`;
- approval required: `pending_approval`;
- active child run: `delegation_running`.

No failure may be converted into a successful response.
