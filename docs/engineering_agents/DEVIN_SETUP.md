# Devin Setup

Do not create a `.devin/` directory unless a future evidence-backed mission
requires it.

Shared policy comes from `AGENTS.md`, `.agents/skills/`, and this directory.

## Devin Terminal

Devin Terminal may operate on the real local checkout when configured on Rafa's
machine.

It may:

- use the local execution overlay when actually present;
- perform repository-only work;
- perform local-required work subject to actual capability;
- act as an alternative local engineering surface to Codex.

## Devin Cloud

Devin Cloud operates in its own cloud environment/VM.

It may:

- perform repository-only work;
- implement the cloud portion of hybrid work;
- run deterministic tests available in that environment;
- push branches or open PRs through its GitHub integration.

It may not claim observations from Rafa's local machine that it did not see.

## Cloud to Local Handoff

Use the same Git branch. The handoff record should include branch, SHAs, files
changed, tests run, proof obtained, proof pending, blockers, and claims not yet
proven. Never include secrets or raw `.env` contents.
