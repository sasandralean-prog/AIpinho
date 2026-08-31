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
4. Record intent/checkpoint/result there when shared work resumes

Do not maintain an independent lock state in this AIpinho copy. That would create split-brain coordination.

## Current redirect checkpoint — 2026-08-30

Pre-documentation checkpoints:

```text
Control main:  04878e51dc81761ebc8c96710d95bb6d01b74528
Envelope main: f1feb07cd41969cae95f71af4bd13028bffbdab5
AIpinho main:  37c5d736df10e614bc90c5e746b544782de66b0c
```

Current external Control truth:

- Lúcio Shell / G3 is operationally validated in governed `current_session` mode.
- The self-hosted runner is `aipinho-pc`, running as `.\aipinho-runner` in the established Windows session.
- G3 child creation uses `CreateProcessW` after fail-closed live parent/session identity validation.
- Control has three versioned governed bootstraps: CMD, Python, and PowerShell.
- Script Catalog remains engine/path/SHA authority; there is no arbitrary caller shell text authority.
- Final loader/native-runtime smokes passed.
- The deliberate CMD `exit 7` smoke correctly produced `failed / SHELL_NONZERO_EXIT` with completed bootstrap proof and no timeout.

## FireTest redirect status

**FireTest is PARKED.**

- Preserve all existing FireTest branches/evidence.
- Do not start a new FireTest merely because G3 is operational.
- Do not infer FireTest readiness from Control shell readiness.
- Resume only after an explicit Lúcio directive and then use the canonical Control `firetest`/`runtime` coordination locks.

A concrete existing FireTest C parked branch is:

```text
agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head cb3846bdbc2372150ba8164a667ef8ef7921cb7e
```

See `CURRENT_STATE.md` in this repository for the local cross-repository mirror summary.

If this file conflicts with Control `COMMUNICATION_SYNC_LUCIO.md`, Control `COMMUNICATION_SYNC.md`, or Control `CURRENT_STATE.md`, **Control wins**.
