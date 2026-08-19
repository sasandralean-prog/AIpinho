# Replit Setup

Replit Agent is a cloud engineering assistant working ON AIpinho.

Read `replit.md` first. It points back to `AGENTS.md` as the canonical
cross-agent policy.

## Allowed Claims

Replit can claim:

- repository inspection;
- static validation;
- unit/regression tests it actually runs;
- cloud integration evidence it actually observes.

Replit cannot claim:

- local GGUF/model validation;
- Pinhoabacaxi Desktop validation;
- Rafa's local corpus validation;
- Windows/local hardware behavior;
- FireTest local public proof.

## Remote and Workspace Modes

When operating without a Replit Git worktree, Replit may inspect repository truth
through the active GitHub connection and may perform remote mutations only when
that connection actually exposes and successfully performs the operation. This
connector-only mode does not provide a local branch, local HEAD, local status, or
local test execution automatically.

When a Replit Project has its own Git worktree, Replit may use the repository's
Git workflow and claim local branch, HEAD, status, and tests only when those facts
are actually observed in that worktree.

In both modes, Replit has no automatic access to Rafa's PC, local GGUFs,
Pinhoabacaxi Desktop, local corpus, Windows hardware, or factual local FireTest.

## Runtime Configuration

This repository intentionally does not add `.replit` in this mission. Replit
support here is instruction support for engineering work, not a claim that
AIpinho runtime is supported as a Replit execution target.
