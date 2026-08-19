---
name: aipinho-context-update
description: Use when updating AIpinho continuity, README, current-state, or wave documents from validated evidence.
---

# AIpinho Context Update

Update continuity/current-state docs only when new evidence supports the change.

## Guardrails

- Do not rewrite context gratuitously.
- Do not let historical documents become current authority accidentally.
- Do not let the Context Pack override code, config, contracts, or validated
  evidence.
- Do not invent Context Pack version bumps.
- Do not smooth over contradictions; name them and classify authority.

## Common Update Targets

- `README.md`
- `DOCUMENT_AUTHORITY.md`
- `AIpinho_context_pack/docs/context/08_WAVE_LEDGER.md`
- `AIpinho_context_pack/docs/context/09_CURRENT_FRONTIER.md`
- `AIpinho_context_pack/docs/context/current_state.json`
- bounded reports under `reports/runtime_consolidation/`

Architecture docs should change only when architecture actually changed.
