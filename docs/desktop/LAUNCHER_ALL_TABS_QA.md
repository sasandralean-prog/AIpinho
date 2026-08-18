# Launcher All Tabs QA

## Scope

Tabs to verify:

- Dashboard
- Chat
- Gemini
- Lucio
- Codex
- Pipeline
- Debugger 2.0
- Config

## RC2 Checks

- Chat main write prompt shows governed result and evidence.
- Dashboard separates backend health from observability health.
- Debugger can filter evidence for agent run/tool invocation.
- Session and chat controls stay usable after backend restart.

## Current Evidence

Sprint 17 backend regressions passed. Manual launcher visual smoke remains recommended before RC2 field acceptance.
