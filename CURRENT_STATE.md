# AIpinho — Current External Control State

_Last updated: 2026-08-30T23:55:00Z by Lúcio_

## Repository role

`sasandralean-prog/AIpinho` is the AIpinho runtime/application repository.

It is **not** the source of Control Plane authority. Canonical governance, authentication, replay, broker authority, Script Catalog, shell execution, lifecycle evidence, and shared coordination live in:

```text
sasandralean-prog/AIpinho-FireTest-Control
```

Unsigned request intake lives in:

```text
sasandralean-prog/AIpinho-Envelope-Requests
```

The AIpinho root `COMMUNICATION_SYNC.md` is a redirect/mirror marker only.

## Repository checkpoint

The pre-documentation AIpinho `main` checkpoint for this refresh is:

```text
37c5d736df10e614bc90c5e746b544782de66b0c
```

That head is a documentation-only communication refresh from 2026-08-27. The Lúcio Shell work since then has occurred in the external Control/Envelope repositories; it has not silently mutated AIpinho runtime source on `main`.

Pre-documentation cross-repository checkpoints:

```text
Control main:  04878e51dc81761ebc8c96710d95bb6d01b74528
Envelope main: f1feb07cd41969cae95f71af4bd13028bffbdab5
AIpinho main:  37c5d736df10e614bc90c5e746b544782de66b0c
```

## Current external Control Plane status

The Lúcio Shell / G3 execution path is now **operationally validated** in Control.

The currently validated execution model is:

```text
self-hosted runner:  aipinho-pc
Windows account:     .\aipinho-runner
execution mode:      current_session
process creation:    CreateProcessW
```

Control verifies actual parent/session identity and returned child-token identity and fails closed if the configured identity does not match the live runner context.

The earlier fresh credentialed-logon path is not the current G3 production path because native runtime initialization remained unreliable under fresh `LogonUserW`-derived contexts.

## Lúcio Shell engine split

Control now uses three governed, versioned engine bootstraps:

```text
bootstrap_cmd.v1.cmd
bootstrap_python.v1.py
bootstrap_powershell.v1.ps1
```

They are selected through Control Script Catalog authority. AIpinho does not gain arbitrary shell authority from this external capability.

The execution principle is:

```text
launcher governs
-> bootstrap executes
-> task produces result
-> lifecycle classifies observed truth
```

## Final G3 proof relevant to AIpinho

Control final validation on 2026-08-30:

- Run #77 / `33342624977`: Win32 / PowerShell loader success.
- Run #78 / `33342716826`: Python native-runtime success.
- Run #79 / `33342785732`: deliberate CMD task `exit 7` correctly produced `failed / SHELL_NONZERO_EXIT`, completed bootstrap proof, and `timed_out=false`.

This proves the governed shell transport/execution/lifecycle path. It does **not** prove any new AIpinho runtime capability or FireTest readiness.

## FireTest status — PARKED

**FireTest remains intentionally parked.**

This repository still contains historical/current FireTest branches and evidence, but the workstream is not presently executing.

Concrete parked checkpoint:

```text
branch: agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head:   cb3846bdbc2372150ba8164a667ef8ef7921cb7e
last head commit: 2026-08-23 — test(firetest): record phase c diagnostic evidence
```

AIpinho `main` has not been advanced by the recent Lúcio Shell work.

Parking means:

- preserve FireTest branches, reports, artifacts, and evidence;
- do not infer `READY` from Control/G3 closure;
- do not start a new FireTest merely because remote governed shell execution now works;
- resume only after an explicit Lúcio directive;
- on resumption, obey canonical Control `firetest`/`runtime` coordination and evidence requirements.

The existing AIpinho README/runtime reports remain the source for the detailed H1C0/R3/FireTest technical frontier. This file only records the current cross-repository operational coordination state.

## Security / authority implication

AIpinho source/runtime work must not bypass Control:

- Ed25519 authentication;
- replay consumption;
- provenance binding;
- capability policy;
- Script Catalog hashes/engine identity;
- execution identity proof;
- Job Object containment;
- spool/ACL evidence;
- lifecycle truth.

Lúcio Shell readiness is transport/execution authority for bounded governed tasks, not generic permission for AIpinho to self-modify or run arbitrary code.

## Current next step

After the three-repository documentation refresh, safely synchronize local AIpinho with `origin/main` using fast-forward-only discipline. Then choose the next runtime engineering workstream explicitly.

FireTest remains parked until that explicit decision is made.

If this file conflicts with Control `CURRENT_STATE.md` or `COMMUNICATION_SYNC_LUCIO.md`, Control wins.
