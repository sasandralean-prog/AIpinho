# Lucio Agent Multimodal Orchestrator

## Purpose

Lucio is the strategic, multimodal agent in the AIpinho multi-agent kernel.
It owns its sessions, public responses, route decisions, event timeline, and
private governed memory. It does not own local execution tools.

## Runtime Flow

1. A user message is stored in the native Agent Session Kernel.
2. A Lucio run is created with the requested operation and capabilities.
3. Governed private/shared memory is loaded as sanitized context.
4. `LucioRoutePolicyService` selects one of:
   - direct strategic response;
   - delegation to Codex for technical execution;
   - delegation to AIpinho for local workspace and artifact operations.
5. Direct responses use the backend-only OpenAI provider.
6. Delegated work creates a `DelegationRequest` with parent/child lineage.
7. The public response reports only confirmed state and evidence references.
8. A private memory candidate may be proposed for later review.

## Multimodal Inputs

Multimodal sources enter the Lucio request as artifact references and sanitized
metadata. Raw files, tokens, and private paths are not copied into public
messages or normal-mode timeline cards. An attachment is evidence, not an
automatic local tool request.

## Safety Boundary

Lucio cannot call local tools directly. Coding, shell, workspace reads/writes,
artifacts, builds, and tests are delegated through the shared policy,
capability, approval, tool gateway, validation, and event contracts.

The OpenAI API key is loaded from `.env.local` by the backend. Status endpoints
expose only a boolean indicating whether the key is configured.
