# AIpinho Context Pack — START HERE

## Purpose

This directory preserves continuity across ChatGPT/Codex accounts, model changes, long pauses, engineering-agent handoffs, and work surfaces.

It is not a chat dump and it is not runtime authority. It is a structured memory layer for philosophy, architecture, workflow, historical waves, current frontier, speculative ideas, and the Rafa + Lúcio working relationship.

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
5. `genome/` as snapshot/design DNA/orientation;
6. historical architecture documents and `archaeology/`;
7. conversation-derived planning/context;
8. speculative ideas.

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

## Current checkpoint

- Context Pack: `v0.3`
- `H1C0.R2 = H1C0_R2_READY_FOR_R3` remains historical baseline.
- `H1C0.R3.01 = OPEN`
- Latest reviewed slice: `H1C0.R3.01.B3.5`
- Latest reviewed verdict: `R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY`
- Branch: `agent/codex/r3-01-b3-5-postcompile-stall-route-boundary`
- Branch HEAD before this context update: `9d5e06c9d2cd8d0a885e53855bd100b4c7a84105`
- Base main: `50af6491b78e662bbd3390a59400aec6f0eb0bb1`
- FireTest 5: `NOT_READY`; not executed in B3.5.
- C gate: `CORRECTIVE_REQUIRED_BEFORE_C`
- B3.3 effect: `PARTIALLY_PROVEN`
- Current blocker: `POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED`
- Current P0: 0
- Current P1: `R3_01_B3_5_P1_CAPABILITY_APPLICABILITY_RESOLUTION_CAPACITY_FRONTIER`
- Current blocking P2: none after report projection correction.
- Next frontier: `H1C0.R3.01.B3.6 — Capability Applicability Resolution Capacity & Admission Control`

Read `09_CURRENT_FRONTIER.md` before proposing implementation work.
