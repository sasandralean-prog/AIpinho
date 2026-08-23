# COMMUNICATION_SYNC

This AIpinho-root file is a **redirect/mirror marker**, not the authoritative coordination ledger.

Canonical shared agent communication lives in:

- Repository: `sasandralean-prog/AIpinho-FireTest-Control`
- Branch: `main`
- File: `COMMUNICATION_SYNC.md`

Required agent read order:

1. Control `main` → `COMMUNICATION_SYNC_LUCIO.md`
2. Control `main` → `COMMUNICATION_SYNC.md`
3. Check active locks/leases there
4. Append intent/checkpoint/result entries there

Do not maintain an independent lock state in this AIpinho copy. That would create split-brain coordination.

Participants:

- `CodexA` — engineer integration / Control Plane / GitHub↔PC
- `CodexFiretest` — FireTest/evidence/AIpinho diagnostic work
- `Lucio` — coordination/review/directives

If this file conflicts with the canonical Control ledger, the Control ledger wins.
