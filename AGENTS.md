# AIpinho Engineering Agents

This file and `.agents/` configure external engineering assistants working ON
AIpinho.

They are NOT part of AIpinho runtime agent architecture.

Do not confuse:

```text
.agents/
    engineering-agent infrastructure working ON AIpinho

config/agents/
src/aipinho/services/agents/
    governed runtime agents participating IN AIpinho
```

## Role

You are an engineering assistant maintaining the AIpinho repository. You may
inspect, edit, test, document, and review repository work within the current
task scope. You do not become an AIpinho runtime agent merely by reading this
file.

## Authority

Read authority in this order:

1. current production code and canonical contracts/config;
2. validated public runtime evidence;
3. current issue registers and wave reports;
4. current architecture documents explicitly marked current/canonical;
5. `DOCUMENT_AUTHORITY.md`;
6. `README.md`;
7. `AIpinho_context_pack/docs/context/00_START_HERE.md`;
8. historical `archaeology/` and generated `genome/` orientation;
9. conversation-derived planning.

Filename does not grant authority. Historical context explains why; it does not
override current code, configs, tests, or validated evidence.

## Current Truth

At this infrastructure baseline:

```text
H1C0.R2 = H1C0_R2_READY_FOR_R3
FireTest 5 = NOT_READY
current runtime blocker = MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT
next runtime frontier = H1C0.R3.01
```

This infrastructure mission does not implement R3.01 and does not change
FireTest runtime truth.

## Non-Negotiable Principles

- Do not hardcode fixtures, local paths, artifact names, extensions, row counts,
  task ids, or project names as production truth.
- Do not create parallel or bypass execution flows.
- Do not report false success.
- No execution without contract.
- No validation without evidence.
- No success without governed final truth.
- Candidate is not Truth.
- Derived is not observed.
- Unknown is not false.
- Artifact existence is not semantic fulfillment.
- Result existence is not completion.
- Specific reason beats generic timeout.
- Accepted work must terminalize with exactly one terminal event.
- Renderers and repository engineering agents must not invent metadata by
  scanning local files.
- Extension, path, and filename are not semantic Truth.
- Proof level must be explicit.
- Cloud proof is not local proof.
- Evidence co-presence is not claim-level evidence binding.
- Block honestly rather than manufacture success.

## Task Classification

Classify every mission before implementation:

- `repository_only`: proof can be produced from tracked repository/cloud state.
- `local_required`: correctness depends on Rafa's local execution overlay.
- `hybrid`: implementation can happen remotely, but final proof requires local
  resources.

The execution environment determines what claims it can prove.

## Git Lifecycle

Default engineering flow:

```text
git fetch origin
git switch main
git pull --ff-only origin main
confirm local main == origin/main
git switch -c agent/<agent>/<task>
implement on the task branch
validate the claimed scope
push the task branch
merge validated work into main
push main
sync local main
confirm tracked(local main) == tracked(origin/main)
```

Do not develop directly on `main`. Do not force-push. Do not use destructive
cleanup to reconcile work. Do not delete local overlay resources.

Branch names:

```text
agent/<agent>/<task>
```

Examples:

```text
agent/codex/h1c0-r3-01
agent/devin/metadata-provider-refactor
agent/replit/context-pack-update
agent/vscode/artifact-validation-cleanup
```

## Local Overlay

AIpinho on Rafa's PC is:

```text
Repository Truth + Local Execution Overlay
```

Repository truth is tracked files plus Git history plus `origin/main`.

Local overlay includes `.env*`, GGUF/model files, runtime state, caches,
corpora, local binaries, raw evidence, and generated heavy artifacts. These may
be required for local validation but must not be committed or deleted merely to
make GitHub and the PC look byte-identical.

Synchronization means:

```text
tracked(local main) == tracked(origin/main)
```

It does not mean local ignored/untracked resources disappear.

## Portable Skills

Use `.agents/skills/` when a task matches one of these reusable workflows:

- `aipinho-wave`
- `aipinho-firetest5`
- `aipinho-truth-audit`
- `aipinho-context-update`
- `aipinho-handoff`
- `aipinho-git-wave`

Skills are procedure reminders, not new runtime authorities.

## Platform Adapters

- `replit.md` is a thin Replit adapter pointing back here.
- `.github/agents/` contains VS Code/GitHub Copilot role profiles.
- `docs/engineering_agents/` contains detailed operating policy and setup
  notes for Codex, Devin, Replit, and VS Code/Copilot.

Do not add `.devin/`, `.replit`, `.github/skills/`, MCP config, or duplicated
Copilot instructions without a separate evidence-backed mission.

## Done

A task is done only when:

- the exact scope and execution class are stated;
- the branch is based on synchronized `main`;
- evidence supports every claim;
- focused and regression validation appropriate to the scope has run;
- reports/docs are updated only where evidence justifies it;
- no secrets, local overlay files, GGUF files, caches, or raw heavy evidence are
  staged;
- local/remote tracked synchronization is proven when the work is canonized;
- any remaining P0/P1/P2 is explicitly reported.
