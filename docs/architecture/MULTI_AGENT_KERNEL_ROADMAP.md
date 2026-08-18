# MULTI AGENT KERNEL ROADMAP

Project: AIpinho
Baseline source: Sprint 0 runtime inventory
Principle: add a coordination kernel without bypassing current governance.

## North Star

AIpinho remains the governance owner. Agent islands such as Gemini Executor, Codex Agent and future Lucio Reviewer can reason, propose, review or execute only through AIpinho contracts, policies, approvals, validation, events and artifacts.

## Kernel Model

The Multi-Agent Kernel should standardize:

- agent identity;
- agent session metadata;
- operation metadata;
- capability requests;
- policy decision references;
- approvals;
- validation references;
- event envelopes;
- artifact ownership;
- UI truth fields.

The kernel should not become a second orchestrator. It should be a registry, normalization and supervision layer that delegates execution to existing AIpinho runtime services.

## Proposed Canonical Agents

| agent_id | role | execution owner | default state |
| --- | --- | --- | --- |
| aipinho_core | local orchestrator/runtime owner | AIpinho runtime | active |
| gemini_executor | external cloud executor/proposer | Gemini Executor island through AIpinho governance | active when env configured |
| codex_agent | local/external Codex CLI proposer/executor island | Codex Agent island through AIpinho governance | active when CLI ready |
| lucio_reviewer | reviewer/supervisor persona or assistant handoff target | future adapter | proposed/disabled |

## Sprint 1 - Contract Foundation

Deliver:

- Schemas: AgentIdentity, AgentSessionRef, AgentOperationRef, AgentCapabilityRequest, AgentEventEnvelope.
- Config: config/agents/agent_registry.yaml, config/agents/agent_kernel_policy.yaml.
- Service: AgentRegistryService, AgentKernelService read-only facade.
- Endpoints: /api/v1/agents/status, /api/v1/agents, /api/v1/agents/{agent_id}, /api/v1/agents/{agent_id}/sessions, /api/v1/agents/operations/{operation_id}.
- Tests: schema/config/import/status, no side effects.

Do not implement new execution.

## Sprint 2 - Agent Adapters

Deliver adapters that map existing islands into the canonical kernel:

- AIpinho chat/task session adapter.
- Gemini Executor session adapter.
- Codex Agent session adapter.
- Event adapter from existing events/traces.
- Artifact ownership mapping.

Tests:

- Histories remain isolated.
- Agent labels are correct.
- No raw/secret leakage.
- UI can inspect canonical metadata without mixing timelines.

## Sprint 3 - Governed Agent Operation Preview

Deliver a preview-only operation planner:

- AgentOperationPreviewService.
- Capability request preview.
- Policy decision reference.
- Approval requirement explanation.
- Validation plan reference.

No side effects. No shell. No patch apply.

## Sprint 4 - Cross-Agent Supervision Timeline

Deliver a supervision timeline that aggregates sanitized events by gent_id, session_id and operation_id:

- Read-only endpoint.
- Debugger 2.0 filters.
- Mobile/Launcher cards if needed.
- Copy sanitized summary.
- Raw hidden by default.

## Sprint 5 - Lucio Reviewer Adapter

Add Lucio as a review/supervision adapter, not an execution bypass:

- Inputs: reports, diffs, operation summaries, validation output.
- Outputs: review findings, risk notes, recommended next step.
- No direct write/shell/apply.
- Optional artifact report generation through artifact lifecycle.

## Sprint 6 - Policy-Constrained Multi-Agent Loop

Only after previous contracts are stable:

- One operation can request review from another agent.
- AIpinho supervisor remains final decision owner.
- Approval/validation remain mandatory for side effects.
- Loop has timeout, max turns, event trace and explicit stop reason.

## Permanent Guardrails

- No agent has free filesystem mutation.
- No agent has free shell.
- No frontend receives API keys or provider tokens.
- No agent writes to source_readonly or forbidden workspaces.
- No success without operation-specific validation.
- No raw by default in chat.
- No reuse of approvals across operation fingerprints.
- No hidden fallback from AIpinho to Gemini/Codex.
- No specific-case prompt/project/workspace rules.

## Sprint 1 Acceptance Criteria

- Current runtime behavior unchanged.
- Agent registry parseable.
- Read-only agent status endpoints work with fake/static metadata.
- Existing Gemini/Codex/AIpinho namespaces remain untouched behaviorally.
- Tests prove no side effects.
- Reports document remaining risks.
