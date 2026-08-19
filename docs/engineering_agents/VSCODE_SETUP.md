# VS Code and GitHub Copilot Setup

Shared policy comes from `AGENTS.md` and `.agents/skills/`.

Workspace custom agent profiles live under:

```text
.github/agents/
```

Installed roles:

- `aipinho-planner.agent.md`
- `aipinho-engineer.agent.md`
- `aipinho-reviewer.agent.md`

These files use minimal `.agent.md` Markdown profiles with frontmatter. They
are role adapters, not a replacement for `AGENTS.md`.

This mission intentionally does not create `.github/copilot-instructions.md`
because duplicating `AGENTS.md` would create a second policy surface without a
separate need.
