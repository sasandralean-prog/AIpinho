# AIpinho Engineering Workflow

## Default wave loop

```text
baseline
→ observed frontier
→ competing hypotheses
→ mandatory diagnostic
→ root-cause classification
→ bounded patch
→ focused tests
→ regressions
→ public diagnostic rerun
→ public clean validation rerun
→ issue register
→ verdict
→ next frontier
```

## Baseline consistency gate

Before starting a new wave, confirm that:
- the intended implementation is present in the target branch;
- README/current-state documents describe the same validated frontier;
- reports and issue registers exist at the claimed validation scope;
- no historical or draft document is silently treated as runtime authority;
- repository paths work on case-sensitive systems.

If Git, code, reports, and current knowledge disagree, resolve that contradiction before widening runtime scope.

## Diagnose before patch

Do not ask first: "what patch will make the test pass?"

Ask: "what boundary is actually failing, and what evidence would prove or disprove each plausible cause?"

## Priority policy

### P0

Truth, governance, terminality, corruption, false-success, authority confusion, or repository/knowledge contradictions that invalidate the working baseline.

### P1

Structural runtime blockers, complexity failures, generic capability/binding defects, nondeterminism.

### P2

Observability/schema/projection problems that affect diagnosis or validation.

### P3

Cosmetic/report formatting; may be deferred.

## Wave boundary

A wave has an architectural owner. Internal iteration is allowed when the next blocker belongs to the same boundary:

```text
diagnostic → patch A → rerun → related blocker → patch B
```

Do not chase unrelated future frontiers forever inside one wave.

## Public proof

Distinguish:
- unit validated;
- regression validated;
- diagnostic public reached;
- clean public validation;
- final public proof.

Never say "publicly validated" when only a unit test exercised the behavior.

## A+B

When determinism matters, compare input identity, projected identity, row model identity, render order, schema digest, cardinality, semantic outcome, and terminal semantics. Wall time may differ; semantics should not.

## Git protocol

```text
sync main
→ create agent/<agent>/<task> branch
→ implement
→ tests
→ required validation for the execution class
→ reports/docs update
→ commit
→ push task branch
→ merge validated branch into main
→ push main
→ synchronize local main
→ prove tracked(local main) == tracked(origin/main)
```

Never use force push or destructive reset as a convenience for reconciling validated history.

## External governed Control Plane

AIpinho has a separate operations repository:

`sasandralean-prog/AIpinho-FireTest-Control`

Its job is to bridge GitHub with the local machine through named governed capabilities and structured evidence. It is not a replacement for the runtime architecture and it is not permission to turn repository text into a terminal.

Current proven loop after B1.0-D / B1.0-E / B1.0-E.1:

```text
allowlisted operation file
→ GitHub Actions workflow_dispatch
→ persistent self-hosted runner aipinho-pc
→ governed dispatcher
→ named capability
→ result.json
→ execution_manifest.json
→ GitHub artifact
→ final truthful verdict
→ optional rerun with explicit attempt provenance
```

The runner is an official Windows service under `\.\aipinho-runner`, startup `Automatic`, status `Running`.

The current Control surface can perform bounded repository observation/synchronization, static governed test profiles/quick validation, runtime lifecycle operations, and Phase 1 diagnostics. Every operation remains constrained by its capability schema, target allowlist, expected provenance, timeout/output budget, and evidence requirements.

### Control Plane truth rules

- Control evidence proves what the Control Plane requested, executed, observed, or packaged at that scope.
- Control evidence does not silently override AIpinho production code/config or validated runtime evidence.
- `repository.pull_ff_only` may fast-forward an expected clean branch; divergence must fail and become evidence rather than trigger hidden merge/rebase/reset.
- GitHub rerun is another attempt of the same workflow request, not permission to update source or repair provenance behind the scenes.
- Read/download an attempt's evidence before rerunning when historical artifact retention matters.
- Runner/service configuration is operations infrastructure; it does not grant new runtime or FireTest authority.

### Current Control limitations

The merged system does **not** currently authorize:

- generic shell;
- arbitrary argv/pytest/path;
- arbitrary dependency installation;
- direct ChatGPT-created operation submission/start;
- governed FireTest execution from Lúcio;
- authenticated `lucio.shell`.

Those capabilities must be admitted explicitly rather than inferred from trust or convenience.

### Agreed Control roadmap

```text
F   -> Governed Operation Submission / start loop
F.1 -> Lúcio-operated bounded FireTest profiles
G   -> Lúcio Authenticated Control Channel
G.1 -> authenticated lucio.shell authority
```

`F` should close the missing start/submission leg without broadening the operation schema into free-form commands.

`F.1` should expose FireTest through static bounded profiles. FireTest commonly needs around ten minutes, so its planned normal execution ceiling is about 15 minutes rather than inheriting the short generic workflow budget.

`G`/`G.1` should treat broad authority as an authentication problem: signed operation hash, replay protection/nonce, short expiry, provenance, and audit evidence. A string claiming `requested_by=Lucio`, a model name, or a conversation ID is informative provenance only unless backed by a trustworthy cryptographic attestation path.

## Engineering-agent infrastructure

Repository engineering assistants should use:

- `AGENTS.md` as the concise shared engineering entrypoint;
- `.agents/skills/` for reusable procedures;
- `docs/engineering_agents/` for detailed operating policy;
- `replit.md` as a thin Replit adapter;
- `.github/agents/` for VS Code/GitHub Copilot role profiles.

These files guide agents working ON AIpinho. They do not define AIpinho runtime
agents and must not be confused with `config/agents/` or
`src/aipinho/services/agents/`.

Task branches should be named:

```text
agent/<agent>/<task>
```

The intended workflow is one active engineering agent and one active task
branch at a time unless explicit coordination/leases permit parallel non-overlapping work.

## Shared-resource coordination

When work touches shared Control/runtime/FireTest resources, use the canonical coordination surfaces in `AIpinho-FireTest-Control`:

1. `COMMUNICATION_SYNC_LUCIO.md`
2. `COMMUNICATION_SYNC.md`

Read them in that order. Logical locks coordinate overlapping work, but a lock never grants an operation that the current mission/capability did not already authorize.

## Local overlay

Tracked synchronization means:

```text
tracked(local main) == tracked(origin/main)
```

It does not mean ignored/untracked local resources such as `.env*`, GGUF
models, runtime state, corpora, or raw evidence are deleted or committed.

## Mobile/manual protocol

When Rafa is operating from a phone:
- read the current GitHub version before preparing a replacement;
- provide complete file contents when replacement is safe;
- identify `PATH`, `ACTION`, and commit message;
- make Git actions independently verifiable;
- avoid dozens of microdiffs when one bounded replacement is clearer;
- do not use full-file replacement for large production code unless the whole file has been verified.

When the governed Control Plane can perform the operation safely, prefer that evidence-producing path over requiring physical access to the PC. If the Control Plane lacks the required authority, state that boundary instead of simulating it with a broader mechanism.

## Issue schema

Prefer separate dimensions:

```text
evidence_status:
  not_proven | probable_with_evidence | proven

resolution_status:
  open | fixing | fixed | validated | deferred

validation_scope:
  none | unit | regression | diagnostic_public | final_public
```

A proven bug is not automatically a resolved bug.

## End-of-wave

State exact verdict, FireTest status, root cause, changes, proof level, open P0/P1/P2, terminality, SpeakerTruth, next frontier, and Git branch/commit/push state.

For Control Plane work, also state operation/run IDs, attempt, artifact/provenance evidence, authority not granted, and whether any shared lock was acquired/released.
