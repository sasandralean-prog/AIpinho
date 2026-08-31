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

## Current redirect checkpoint — benchmark handoff

Benchmark checkpoint immediately before the final documentation refresh:

```text
Control main:  b43e368a229ac941fb2e9b31d499d58d85906e0d
Envelope main: a462adce003a52daf75a236cf3c72b62c4de4df3
AIpinho main:  091ae4442f217b9133c20048e0289d8b3690ca9c
```

Current external Control truth:

- Lúcio Shell / G3 is operationally validated and benchmark-frozen as `G3_BASELINE_VALIDATED`.
- Canonical benchmark report: `reports/control_g3_benchmark_baseline_20260830.md` in Control.
- The self-hosted runner is `aipinho-pc`, running as `.\aipinho-runner` in the established Windows session.
- G3 child creation uses `CreateProcessW` after fail-closed live parent/session identity validation.
- Control has three versioned governed bootstraps: CMD, Python, and PowerShell.
- Script Catalog remains engine/path/SHA authority; there is no arbitrary caller shell-text authority.
- Positive native/runtime paths are proven for PowerShell and Python.
- Deliberate CMD `exit 7` is truthfully classified as `SHELL_NONZERO_EXIT`, not timeout.
- Catalog mismatch is rejected before shell.
- Output ceiling fails closed with `SHELL_OUTPUT_LIMIT_EXCEEDED`.
- A fixed true deadline is classified as `SHELL_TIMEOUT`.
- Exact rerun of a consumed signed authorization is rejected as `AUTH_ALREADY_CONSUMED` without a second dispatch.

Explicit benchmark residuals/capability gaps:

- the fixed deadline run did not establish positive launcher-level process-tree kill proof because its terminal marker reported `process_tree_terminated=false`;
- `g3.test.control_quick_regression.cmd` is currently `NOT_READY` because the deterministic Python runtime does not contain `pytest`;
- dependency provisioning must become a separate governed authority rather than an ad hoc install inside G3.

## Next coordinated workstream

After safe synchronization of the three repositories, the next explicit workstream is:

```text
CONTROL-H1 — Identity & Session Control
```

H1 starts from explicit provider/account/session representations and observation contracts for Codex CLI and other admitted agents.

Key coordination invariants:

- account identity is not credential material;
- no password/token/cookie/private key/browser-session secret is stored in repository docs or ordinary evidence;
- account/session transitions must be explicit governed capabilities when admitted;
- observed post-transition identity becomes evidence;
- quota/session status is observable but not authority by itself;
- agent promptability does not grant generic shell or source-mutation authority;
- all G3 authentication/replay/catalog/identity/containment/lifecycle controls remain underneath H1.

## FireTest redirect status

**FireTest is PARKED.**

- Preserve all existing FireTest branches/evidence.
- Do not start a new FireTest merely because G3 is benchmark-validated or H1 is beginning.
- Do not infer FireTest readiness from Control shell readiness.
- Resume only after an explicit Lúcio directive and then use the canonical Control `firetest`/`runtime` coordination locks.

A concrete existing FireTest C parked branch is:

```text
agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head cb3846bdbc2372150ba8164a667ef8ef7921cb7e
```

## Synchronization handoff

Before H1 implementation:

- fast-forward local Control, Envelope, and AIpinho from remote `main`;
- preserve local/untracked evidence;
- do not use `git clean` or destructive reset to force cleanliness;
- do not pop the old Envelope pre-sync stash onto `main` during synchronization.

See `CURRENT_STATE.md` in this repository for the local cross-repository mirror summary.

If this file conflicts with Control `COMMUNICATION_SYNC_LUCIO.md`, Control `COMMUNICATION_SYNC.md`, or Control `CURRENT_STATE.md`, **Control wins**.
