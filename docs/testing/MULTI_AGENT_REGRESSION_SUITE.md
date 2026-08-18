# Multi-Agent Regression Suite

The multi-agent regression suite protects the operational contracts for AIpinho, Lucio, Codex and Gemini.

It is designed as a local, deterministic safety net:

- It uses temporary fixtures and fake provider adapters.
- It does not require real API keys or internet access.
- It does not mutate user workspaces.
- It validates both safety and governed operational freedom.
- It writes sanitized reports to `reports/regression/`.

## Commands

```powershell
python tests\multi_agent\run_multi_agent_regression.py --quick
python tests\multi_agent\run_multi_agent_regression.py --all
```

## Suites

- golden paths: sessions, messages, tools, artifacts, delegation and self-healing.
- freedom: safe read/write/shell flows that should not be blocked by bureaucracy.
- security: source_readonly, forbidden workspaces, dangerous shell and secret redaction.
- speaker truth: user-facing success claims must have evidence.
- UI contracts: raw hidden by default, details sanitized, token-safe artifact behavior.

## Current Status

The Sprint 14 quick suite passed with 15 tests.

