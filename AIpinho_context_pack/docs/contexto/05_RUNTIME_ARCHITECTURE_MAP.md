# AIpinho Runtime Architecture Map

> Orientation document. Current production code, canonical contracts/config, and validated runtime evidence remain authoritative.

## Two layers that must not be collapsed

AIpinho has a philosophical/cognitive model and a concrete implemented runtime flow. They describe different abstraction levels.

### Philosophical / cognitive model

```text
language
→ meaning
→ intention
→ contract
→ intermediate representation / plan
→ governed execution
→ evidence
→ validation
→ completion
→ SpeakerTruth
→ user-facing operational truth
```

This explains why the system exists and what epistemic boundaries it protects.

### Implemented canonical runtime

Based on `AIpinho_Canonical_Flow.md`:

```text
Prompt
→ Conversation Context
→ SemanticIntentResolution
→ RuntimeContractBundle
→ EffectivePolicyDecision
   ├─ allowed → ExecutionPlan
   ├─ ask → ApprovalRequest → ApprovalDecision → ExecutionPlan
   └─ deny/block → Blocked Response Contract
→ UniversalTaskRuntime
   ├─ RuntimeTimeline
   ├─ ArtifactRuntime
   └─ Validation
→ Completion
→ SpeakerTruth / RuntimeTruth
→ Chat / Mobile / API / Launcher
```

The philosophical chain must not replace the implemented names. The concrete flow must not be mistaken for a complete theory of cognition.

## Canonical authorities

- `SemanticIntentResolution` — intent and semantic-context authority.
- `RuntimeContractBundle` — carrier of operational meaning.
- `EffectivePolicyDecision` — only permission authority.
- `UniversalTaskRuntime` — only execution authority.
- `RuntimeTimeline` — operational-state authority.
- `ArtifactRuntime` — governed artifact lifecycle/evidence boundary.
- Validation and Completion — semantic fulfillment boundary.
- `SpeakerTruth` / `RuntimeTruth` — final authority for user-facing success claims.

Routers and clients are adapters. They must not create parallel intent, permission, execution, state, validation, or final-truth authorities.

## Runtime boundaries

### Semantic ingress

Interprets the request and classifies the operation. Request wording is not itself a runtime contract.

### Operation contract

Defines what is allowed, expected, and required. Execution should not outrun the contract.

### Governed runtime

Owns execution, checkpoints, budgets, and terminality. Accepted work must terminalize, and known-stage failure should preserve a specific reason.

### Observation / perception

Produces governed representations of observable reality and keeps missing, unsupported, failed, candidate, observed, and derived states distinct.

### Fact projection + source binding

Facts remain connected to evidence and provenance. Source identity must not be inferred from superficial locators.

### Artifact runtime

Materializes governed payloads. A renderer must not scan the filesystem to invent metadata. Artifacts require task, task-run, producer, and event binding to become strict evidence.

### Persistence

R2 established bounded persistence checkpoints, payload refs for large semantic subtrees, atomic content writes, failure cleanup, sharded manifest/index behavior, and legacy registry work outside the hot path.

### CSV/tabular materialization

R2.16–R2.17 established explicit cardinality domains, deterministic row/order digests, stall-versus-budget semantics, and indexed per-render cell lookup with public fallback scan reaching zero.

### Identity validation

R2.18 established:
- stable entity identity: `entity_id`;
- locator/display: filename, name, relative path;
- routing hints: extension, media type, root role;
- semantic media identity: title/artist/album-style claims requiring governed observation evidence.

### Completion

Completion is semantic, not merely operational. A blocked run can terminalize correctly without fulfilling the request.

### SpeakerTruth

Final communication boundary controlling what can safely be claimed.

## Agent topology

### 1. AIpinho internal runtime agents

These participate inside AIpinho's governed runtime/cognition. Their configuration and implementation live under areas such as:

```text
config/agents/
src/aipinho/services/agents/
```

They are **in AIpinho**.

### 2. External agent islands

The current registry describes:

- AIpinho — `provider: local`, `role: local_orchestrator`, enabled;
- Codex — `provider: local_cli`, `role: code_executor`, enabled;
- Gemini — `provider: cloud`, `role: cloud_agent`, enabled;
- Lúcio — `role: multimodal_strategic_orchestrator`, `disabled_by_config`.

Codex and Gemini are distinct agent/execution islands governed through the platform. They are not equivalent internal cognitive roles of AIpinho.

`hybrid_execution_policy.yaml` explicitly models Codex execution modes and `interpretation_islands`, currently allowing Gemini as an interpretation island without granting ungoverned local execution.

### 3. Engineering agents

Engineering assistants work **on the AIpinho repository**. Examples include Codex, Replit, VS Code/Copilot, Devin, and future repository-local agent instructions or skills.

Planned repository surfaces may include:

```text
AGENTS.md
.agents/skills/
replit.md
.github/agents/
```

These are not automatically part of the AIpinho runtime.

Critical namespace rule:

```text
.agents/ and repository assistant instructions
    = engineering agents working ON AIpinho

config/agents/ and src/aipinho/services/agents/
    = governed agents participating IN AIpinho
```

Do not mix the namespaces.

## Governed delegation

Delegation is implemented, not merely speculative.

Current policy includes:
- maximum depth: 3;
- maximum child runs per parent: 10;
- cycle detection: enabled;
- governed routes between Lúcio, AIpinho, Codex, and Gemini;
- explicit denial of direct Gemini → Codex and Codex → Gemini routes.

Configuration proves that a route is modeled and allowed; it does not by itself prove successful end-to-end execution in every environment.

## Platform surfaces

Chat, API, Mobile, and Launcher are clients/surfaces of the governed runtime. The launcher under `apps/launcher/` has its own bootstrap, process management, watchdog, tray, and UI responsibilities.

```text
AIpinho Core/runtime ≠ Launcher/platform surface
```

Clients must consume canonical status/truth instead of inventing independent finality.

## Model layer

AIpinho uses a configured multimodel fleet and model-runtime infrastructure. Avoid freezing a model count in durable context because registry contents evolve. Current configuration and capability routing are authoritative.

## Important distinctions

```text
artifact created ≠ contract fulfilled
result persisted ≠ semantic success
candidate produced ≠ Truth
stable entity identity ≠ semantic media identity
evidence exists somewhere ≠ evidence supports this exact claim
configured route ≠ publicly validated execution
engineering agent ≠ AIpinho runtime agent
filename says final ≠ document is authoritative
```

## Current transition

R2 focused on reliable representation, execution, observation, terminality, materialization, and honest refusal.

R2.18 is now reconciled into `main`.

Before R3 begins, the repository/knowledge consistency gate must align paths, current-state documents, authority markers, and handoff material.

R3.01 then begins with a different problem: the representation exists, but the public runtime lacks a configured governed capability to acquire semantic media identity evidence.

