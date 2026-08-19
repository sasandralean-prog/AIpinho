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
branch at a time.

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
