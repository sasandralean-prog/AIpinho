---
name: aipinho-handoff
description: Use when onboarding or transferring AIpinho repository work between Codex, Devin, Replit, VS Code/Copilot, or future engineering assistants.
---

# AIpinho Handoff

Use this skill before another engineering assistant or environment continues a
task.

## Read First

- `AGENTS.md`
- `DOCUMENT_AUTHORITY.md`
- `AIpinho_context_pack/docs/context/00_START_HERE.md`
- current Git state
- current frontier
- latest relevant evidence/reports

## Handoff Record

Include:

- task name;
- execution class: `repository_only`, `local_required`, or `hybrid`;
- agent/environment;
- base branch and base SHA;
- current branch and head SHA;
- changed files;
- tests already run;
- validation scope already proven;
- validation still required locally;
- known blockers;
- claims explicitly not proven;
- local capability categories required.

Never include secret values, credentials, or raw `.env` contents.
