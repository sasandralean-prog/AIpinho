# AIpinho Multi-Agent RC1

Date: 2026-06-13

## Summary

RC1 consolidates the multi-agent kernel with sessions, timelines, governed tools, policy/autoapproval, delegation, memory boundaries, dashboard/debugger, self-healing and regression gates.

## Included Agents

- AIpinho.
- Lucio.
- Codex.
- Gemini.

## Validation

- Python compileall: passed.
- Multi-agent regression quick: 15 passed.
- Multi-agent regression all: 18 passed.
- Sprint 16 LAN/Tailscale smoke: passed for 9088.
- Sprint 16 physical mobile dashboard smoke: backend online, observability degraded by field-trial state.
- Sprint 16 hotfix: capability aliases and Gemini delegated-operation mapping now allow Lucio/Gemini to delegate artifact/write-style requests to AIpinho without the previous capability/operation false block.

## Known Limits

- Main AIpinho chat still needs a unified write bridge for explicit safe create_file/modify_file prompts; addressed in RC2.
- Full visual mobile and launcher QA should be rerun before long production-like sessions.
- Regression coverage is useful but still initial.
- Self-healing detectors are conservative.

## Security Notes

- No API keys belong in mobile, launcher, reports or raw logs.
- Artifact downloads use Authorization headers.
- Raw remains hidden by default.
