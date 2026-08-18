# Gemini Agent Cloud Delegation

## Purpose

Gemini is a separate cloud agent island connected to the shared multi-agent
kernel. It can answer directly through the configured Gemini provider, but local
filesystem, workspace, shell, validation and artifact work is delegated to the
AIpinho agent.

## Runtime Flow

```text
Gemini session
-> GeminiExecutorService.send
-> Agent Session Kernel parent run
-> Memory Gateway context
-> Gemini policy decision
-> direct cloud response
   or
-> DelegationRequest Gemini -> AIpinho
-> child run
-> governed local execution
-> event and evidence references
```

The cloud agent never receives permission to bypass the local Tool Gateway.
`GEMINI_AGENT_ALLOW_DIRECT_LOCAL_TOOLS=false` is the default.

## Separation

- Gemini messages use `GeminiExecutorSessionStore`.
- Agent Kernel runs use `agent_id=gemini`.
- AIpinho child runs keep their own agent identity.
- The main AIpinho chat history is not reused.
- Cloud warnings are visible in the Gemini view-model.

## Governance

Local work is recognized from workspace context, target paths, operation type
or requested capabilities. The service then creates a `DelegationRequest` with:

- parent agent and run;
- target agent `aipinho`;
- execution mode;
- workspace and capability requirements;
- sanitized constraints;
- memory references;
- expected evidence.

If delegation is disabled and direct local tools are not allowed, the request is
blocked with `gemini_local_execution_requires_delegation`.

## Memory

At run start, the Memory Gateway loads validated Gemini, shared, project,
regression and user preference context. At successful completion, Gemini creates
a private `memory:gemini` candidate. Memory failures are warnings and do not
silently change execution semantics.

## Events And View-Model

Gemini exposes:

- `GET /api/v1/gemini-executor/runs/{run_id}/events`
- `GET /api/v1/gemini-executor/sessions/{session_id}/view-model`

The view-model keeps raw hidden, does not include tokens in URLs, and identifies
the active parent run, delegation and child run through sanitized metadata.

## Security

- API keys are backend environment variables only.
- Key values are absent from config status, events and reports.
- Local side effects require delegation and shared governance.
- Source read-only and forbidden workspace decisions remain owned by policy.
- Direct provider failures become controlled errors without local side effects.
