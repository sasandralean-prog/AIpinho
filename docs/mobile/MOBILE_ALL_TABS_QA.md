# Mobile All Tabs QA

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

- Backend status uses core backend semantics.
- Observability degradation is not shown as backend offline.
- Chat can show governed write success, block or clarification.
- Raw/debug data remains hidden unless explicitly opened.
- Artifact and evidence buttons remain visible when present.

## Current Evidence

Sprint 17 backend regressions passed. Full visual pass should be rerun on physical device or emulator before RC2 field acceptance.
