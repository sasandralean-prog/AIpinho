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

Current redirect checkpoint — 2026-08-27:

- Control PR #20 merged: `CONTROL B1.0-G.1.2 — psutil identity observation shim`.
- Control PR #21 merged: `CONTROL B1.0-G.2 — governed envelope broker`.
- G.1 `lucio.shell` is still not live-validated.
- G.2 broker is implemented and merged, but not live-validated.
- `sequence=5` must not be reused; the next live smoke must use `sequence=6`.
- See `CURRENT_STATE.md` in this repository for a local mirror summary.
- If this file conflicts with Control `COMMUNICATION_SYNC_LUCIO.md` or Control `CURRENT_STATE.md`, Control wins.

If this file conflicts with the canonical Control ledger, the Control ledger wins.
