# Engineering Agents

This directory documents engineering assistants that work ON the AIpinho
repository.

It does not define AIpinho runtime agents.

## Three Agent Categories

```text
AIpinho internal runtime agents
    config/agents/
    src/aipinho/services/agents/

external agent islands
    governed participants/executors through AIpinho runtime topology

engineering agents
    Codex, Devin, Replit, VS Code/Copilot, and future assistants working ON
    the repository
```

## Entrypoints

Read in this order for engineering work:

1. `AGENTS.md`
2. `DOCUMENT_AUTHORITY.md`
3. `AIpinho_context_pack/docs/context/00_START_HERE.md`
4. this directory's policy documents
5. the relevant `.agents/skills/*/SKILL.md`

## Policy Files

- `PLATFORM_MATRIX.md` - factual capability boundaries by engineering surface.
- `GIT_WORKFLOW.md` - branch, merge, push, and final sync protocol.
- `LOCAL_EXECUTION_OVERLAY.md` - local-only resources and repository truth.
- `VALIDATION_AUTHORITY.md` - proof levels and environment-specific claims.
- `CODEX_SETUP.md` - Codex-local guidance.
- `DEVIN_SETUP.md` - Devin Terminal and Devin Cloud guidance.
- `REPLIT_SETUP.md` - Replit Agent guidance.
- `VSCODE_SETUP.md` - VS Code/GitHub Copilot guidance.

## Core Rule

One active engineering agent should own one active task branch at a time. Agents
may alternate through Git handoff, but simultaneous uncoordinated writers are
not the intended workflow.
