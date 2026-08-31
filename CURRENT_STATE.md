# AIpinho — Current External Control State

_Last updated: 2026-08-31T01:50:00Z by Lúcio_

## Repository role

`sasandralean-prog/AIpinho` is the AIpinho runtime/application repository.

It is **not** the source of Control Plane authority. Canonical governance, authentication, replay, broker authority, Script Catalog, shell execution, lifecycle evidence, the frozen G3 benchmark baseline, and the next H1 control workstream live in:

```text
sasandralean-prog/AIpinho-FireTest-Control
```

Unsigned request intake lives in:

```text
sasandralean-prog/AIpinho-Envelope-Requests
```

The AIpinho root `COMMUNICATION_SYNC.md` is a redirect/mirror marker only.

## Repository checkpoint

Benchmark checkpoint immediately before this final documentation refresh:

```text
Control main:  b43e368a229ac941fb2e9b31d499d58d85906e0d
Envelope main: a462adce003a52daf75a236cf3c72b62c4de4df3
AIpinho main:  091ae4442f217b9133c20048e0289d8b3690ca9c
```

The recent G3 benchmark work occurred in external Control/Envelope repositories. It did not silently mutate AIpinho runtime source on `main`.

## Current external Control Plane status

The Lúcio Shell / G3 execution path is operationally validated and benchmark-frozen as:

```text
G3_BASELINE_VALIDATED
```

Canonical benchmark report in Control:

```text
reports/control_g3_benchmark_baseline_20260830.md
```

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

Control uses three governed, versioned engine bootstraps:

```text
bootstrap_cmd.v1.cmd
bootstrap_python.v1.py
bootstrap_powershell.v1.ps1
```

They are selected through Control Script Catalog authority. AIpinho does not gain arbitrary shell authority from this external capability.

The execution principle remains:

```text
launcher governs
-> bootstrap executes
-> task produces result
-> lifecycle classifies observed truth
```

## G3 benchmark proof relevant to AIpinho

The frozen Control benchmark includes:

- Run #77 / `33342624977`: Win32 / PowerShell native-loader success.
- Run #78 / `33342716826`: Python native-runtime success.
- Run #79 / `33342785732`: deliberate CMD exit `7` correctly produced `failed / SHELL_NONZERO_EXIT`, completed bootstrap proof, and `timed_out=false`.
- Run #85 / `33344270152`: invalid Script Catalog version rejected before shell.
- Run #86 / `33344388918`: deterministic CMD/Python import path success.
- Run #88 / `33344524120`: output ceiling failed closed with `SHELL_OUTPUT_LIMIT_EXCEEDED`.
- Run #89 / `33344739293`: fixed 5 s task under 1 s grant truthfully produced `SHELL_TIMEOUT`.
- Run #90 / `33344847751`, attempt 2: consumed signed authorization rejected as `AUTH_ALREADY_CONSUMED`, with no second dispatch.

This proves the governed transport/execution/lifecycle substrate. It does **not** prove any new AIpinho runtime capability or FireTest readiness.

## Benchmark-discovered truths relevant to future runtime work

The benchmark exposed one deterministic environment dependency in Control CMD profiles and repaired it by binding Python to an absolute governed runtime path rather than `%ProgramFiles%`.

A later quick-regression profile then reached Python correctly but found that the selected deterministic runtime does not contain `pytest`.

The current Control disposition is:

```text
g3.test.control_quick_regression.cmd = NOT_READY
```

until a separate governed test-runtime/dependency-provisioning authority exists.

AIpinho must not interpret that gap as permission to mutate Control's Python environment, install dependencies ad hoc, or bypass the Script Catalog.

The fixed deadline benchmark also proved `SHELL_TIMEOUT`, but did not provide positive launcher-level process-tree kill proof in that run because the terminal marker reported `process_tree_terminated=false`. That remains an explicit Control H1 hardening/observability item rather than a hidden claim.

## Next external workstream — CONTROL-H1

After repository synchronization, the next Control workstream is:

```text
CONTROL-H1 — Identity & Session Control
```

Initial H1 boundary relevant to AIpinho:

- provider/account/session identity will become explicit Control representations for Codex CLI and other admitted agents;
- account identity is metadata/authority state, never credential material;
- passwords, tokens, cookies, private keys, browser/session secrets, or equivalent credentials must not flow into AIpinho source, ordinary child evidence, or repository documents;
- account/session transitions, when later admitted, must be explicit governed capabilities;
- observed post-transition identity becomes evidence;
- quota/session state may be observable but is not authority by itself;
- an agent able to receive a prompt does not gain arbitrary shell or AIpinho mutation authority.

H1 must preserve the frozen G3 lower-layer invariants: authentication, replay, Script Catalog, execution identity proof, Job Object containment, secret scrubbing, deadline/output controls, and lifecycle truth.

## FireTest status — PARKED

**FireTest remains intentionally parked.**

This repository still contains historical/current FireTest branches and evidence, but the workstream is not presently executing.

Concrete parked checkpoint:

```text
branch: agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head:   cb3846bdbc2372150ba8164a667ef8ef7921cb7e
last head commit: 2026-08-23 — test(firetest): record phase c diagnostic evidence
```

Parking means:

- preserve FireTest branches, reports, artifacts, and evidence;
- do not infer `READY` from Control/G3 closure or benchmark validation;
- do not start a new FireTest merely because remote governed shell execution works or H1 begins;
- resume only after an explicit Lúcio directive;
- on resumption, obey canonical Control `firetest`/`runtime` coordination and evidence requirements.

The existing AIpinho README/runtime reports remain the source for the detailed H1C0/R3/FireTest technical frontier. This file records only the current cross-repository operational coordination state.

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
- deadline/output controls;
- lifecycle truth.

Lúcio Shell readiness is transport/execution authority for bounded governed tasks, not generic permission for AIpinho to self-modify or run arbitrary code.

## Current next step

1. Complete the three-repository benchmark-to-H1 documentation refresh.
2. Safely synchronize local AIpinho with `origin/main` using fast-forward-only discipline while preserving local evidence/untracked files.
3. Synchronize Control and Envelope the same way; do not use destructive cleanup.
4. After all three repositories are synchronized, begin `CONTROL-H1 — Identity & Session Control` in Control.
5. FireTest remains parked until explicitly resumed.

If this file conflicts with Control `CURRENT_STATE.md` or `COMMUNICATION_SYNC_LUCIO.md`, Control wins.
