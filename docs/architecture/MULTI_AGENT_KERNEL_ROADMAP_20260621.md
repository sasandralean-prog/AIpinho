# Multi-Agent Kernel Roadmap - 2026-06-21

## Current Baseline

The foundational Agent Session Kernel is already implemented. AIpinho remains the canonical policy, task-runtime, artifact, approval, validation, and patch-apply owner.

## Next Authorized Work

Only when explicitly requested, build UI/event consumption on top of the current kernel. Do not introduce a second tool gateway, delegation loop, or task runtime.

## Permanent Constraints

- Agent sessions remain isolated by `agent_id` and `session_id`.
- Normal chat never exposes raw payloads or secrets.
- Models may propose patch previews but never apply them.
- Patch apply stays behind quality, approval, and validation gates.
- Agent islands may not bypass workspace policy or governed tools.
