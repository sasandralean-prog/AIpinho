# AIpinho Context Pack — START HERE

## Purpose

This directory preserves continuity across ChatGPT/Codex accounts, model changes, long pauses, engineering-agent handoffs, and work surfaces.

It is not a chat dump and it is not runtime authority. It is a structured memory layer for philosophy, architecture, workflow, historical waves, current frontier, speculative ideas, the Rafa + Lúcio working relationship, and the external governed Control Plane used to bridge GitHub with the local PC.

## Read order

For engineering assistants working on the repository, read `AGENTS.md` and
`DOCUMENT_AUTHORITY.md` before the Context Pack.

1. `00_START_HERE.md`
2. `01_AIPINHO_PHILOSOPHY.md`
3. `02_LUCIO_RAFA_WORKING_RELATIONSHIP.md`
4. `03_ENGINEERING_WORKFLOW.md`
5. `04_PROMPT_STYLE.md`
6. `05_RUNTIME_ARCHITECTURE_MAP.md`
7. `06_FIRETEST5.md`
8. `07_H1_TO_H4_ROADMAP.md`
9. `08_WAVE_LEDGER.md`
10. `09_CURRENT_FRONTIER.md`
11. `10_IDEA_LAB.md`
12. `11_HANDOFF_PROTOCOL.md`
13. `current_state.json`

## Authority hierarchy

When sources disagree, prefer:

1. current production code and canonical contracts/config;
2. validated public runtime evidence;
3. current issue registers and wave reports;
4. architecture documents explicitly marked current/canonical;
5. current repository/context orientation documents;
6. generated snapshots such as `genome/`;
7. historical architecture documents and `archaeology/`;
8. conversation-derived planning/context;
9. speculative ideas.

External Control Plane code/evidence has authority only for what the Control Plane itself did, requested, observed, or proved. It does not outrank AIpinho production code/config or validated runtime evidence when describing AIpinho runtime truth.

Filename does not grant authority. A file named `FinalArchitecture` may still be a draft. A file's internal status, date, implementation evidence, and agreement with current code matter more than its title.

Historical material is never automatic runtime authority. Code/config/evidence still win over this Context Pack.

## Context rules

Context should obey AIpinho's own philosophy:
- separate observed from inferred;
- separate current from historical;
- separate architecture from aspiration;
- preserve contradictions instead of smoothing them away;
- treat memory as orientation, not permission to override code or evidence.

## Agent vocabulary

Never collapse these categories:

1. **AIpinho internal runtime agents** — components participating inside AIpinho's governed cognition/runtime, represented under areas such as `config/agents/` and `src/aipinho/services/agents/`.
2. **External agent islands** — distinct executors/interpreters accessible through AIpinho's platform or governance, such as Codex and Gemini.
3. **Engineering agents** — assistants working on the AIpinho repository, such as Codex, Replit, VS Code/Copilot, Devin, or future `.agents/` workflows. They are not automatically runtime agents.
4. **External Control Plane** — the separate `AIpinho-FireTest-Control` repository and self-hosted runner used to execute named governed operations on the local machine and return structured evidence. It is an operations/engineering layer, not an AIpinho runtime-agent namespace.

## Current runtime checkpoint

The runtime checkpoint retained by Context Pack v0.4 remains the last reviewed state already recorded by v0.3:

- `H1C0.R2 = H1C0_R2_READY_FOR_R3` remains historical baseline.
- `H1C0.R3.01 = OPEN`
- Latest reviewed slice in this pack: `H1C0.R3.01.B3.5`
- Latest reviewed verdict: `R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY`
- Branch recorded by that checkpoint: `agent/codex/r3-01-b3-5-postcompile-stall-route-boundary`
- FireTest 5: `NOT_READY` in that recorded runtime checkpoint.
- C gate: `CORRECTIVE_REQUIRED_BEFORE_C`
- Current blocker in that checkpoint: `POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED`
- Current P0: 0
- Current P1: `R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER`
- Current blocking P2: none after report projection correction.
- Next runtime frontier in that checkpoint: `H1C0.R3.01.B3.6 — Capability Applicability Resolution Capacity & Admission Control`

Read `09_CURRENT_FRONTIER.md` and then inspect current Git/code/reports before proposing runtime implementation work. The runtime branch may have advanced after this pack update.

## Current Control Plane checkpoint

Context Pack: `v0.4`

Control repository:
`sasandralean-prog/AIpinho-FireTest-Control`

Observed Control `main` after final B1.0-E service integration and README refresh:
`fe9daa384ff83c0c417677f07d4bb317301f812e`

Integrated state:

```text
B1.0-D   = merged
B1.0-E   = merged
B1.0-E.1 = merged
```

The self-hosted runner `aipinho-pc` is configured as an official Windows service under `\.\aipinho-runner`, with startup `Automatic` and status `Running`.

Service-backed validation passed through a real GitHub Actions run and rerun. Run `32848578948` reached attempt `2`, produced artifact `9563333072`, recorded `is_rerun_attempt=true`, returned `completed`, and verified request/result hashes.

Current Control authority is still bounded to named capabilities. There is no generic shell, no arbitrary argv/pytest/path authority, and no ChatGPT-authenticated `lucio.shell` yet.

Agreed Control roadmap:

```text
F   -> Governed Operation Submission / start loop
F.1 -> Lúcio-operated bounded FireTest profiles
G   -> Lúcio Authenticated Control Channel
G.1 -> authenticated lucio.shell authority
```

For future FireTest control, use a larger profile-specific timeout than the current short workflow path; the planned normal ceiling is about 15 minutes.
