# AIpinho — Current External Control State

_Last updated: 2026-09-04 by Lúcio_

## Repository role

`sasandralean-prog/AIpinho` is the AIpinho runtime/application repository.

It is **not** the source of Control Plane authority. Canonical governance, authentication, replay, broker authority, Script Catalog, governed engineering execution, and current CONTROL-H3/H3-J state live in:

```text
sasandralean-prog/AIpinho-FireTest-Control
```

Unsigned request intake lives in:

```text
sasandralean-prog/AIpinho-Envelope-Requests
```

The AIpinho root `COMMUNICATION_SYNC.md` is a redirect/mirror marker only.

## 2026-09-04 coordination correction

The older sections below preserve the historical G3/H1 checkpoint that originally parked FireTest. They are retained as provenance, not as the current Control roadmap.

Current cross-repository truth is:

```text
Control progressed through CONTROL-H1 and CONTROL-H2.
CONTROL-H3-A through H3-H are accepted at their defined scopes.
CONTROL-H3-I has end-to-end authority-compression acceptance, including a second independent promotion.
CONTROL-H3-J has started progressive FireTest re-entry.
FireTest broad/global READY is NOT claimed.
```

The FireTest product workstream is therefore no longer globally `PARKED`; it is in **progressive governed re-entry**, beginning from the narrow historical FireTest-C/FFmpeg diagnostic checkpoint.

## Historical repository checkpoint

Benchmark checkpoint immediately before the 2026-08-31 documentation refresh:

```text
Control main:  b43e368a229ac941fb2e9b31d499d58d85906e0d
Envelope main: a462adce003a52daf75a236cf3c72b62c4de4df3
AIpinho main:  091ae4442f217b9133c20048e0289d8b3690ca9c
```

The G3 benchmark work occurred in external Control/Envelope repositories. It did not silently mutate AIpinho runtime source on `main`.

## Historical external Control Plane baseline

The Lúcio Shell / G3 execution path was operationally validated and benchmark-frozen as:

```text
G3_BASELINE_VALIDATED
```

Canonical benchmark report in Control:

```text
reports/control_g3_benchmark_baseline_20260830.md
```

The validated execution model remains relevant as a lower-layer invariant:

```text
self-hosted runner:  aipinho-pc
Windows account:     .\aipinho-runner
execution mode:      current_session
process creation:    CreateProcessW
```

Control verifies actual parent/session identity and returned child-token identity and fails closed if the configured identity does not match the live runner context.

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

This proved the governed transport/execution/lifecycle substrate. It did **not** by itself prove any AIpinho runtime capability or FireTest readiness.

## Historical CONTROL-H1 transition

The 2026-08-31 document named CONTROL-H1 — Identity & Session Control as the next external workstream. That workstream and CONTROL-H2 have since progressed in the external Control repository; consult Control `CURRENT_STATE.md` for current authority rather than this historical section.

The frozen lower-layer principles remain relevant:

- account identity is metadata/authority state, never credential material;
- passwords, tokens, cookies, private keys, browser/session secrets, or equivalent credentials must not flow into AIpinho source or ordinary child evidence;
- account/session transitions require explicit governed capabilities;
- observed post-transition identity is evidence;
- quota/session state is observable but is not authority by itself;
- an agent able to receive a prompt does not gain arbitrary shell or AIpinho mutation authority.

## FireTest status — PROGRESSIVE GOVERNED RE-ENTRY

FireTest is no longer globally parked. Re-entry has been explicitly authorized and is being staged through CONTROL-H3-J. This does **not** mean FireTest 5 is `READY` and does not authorize unrestricted live execution.

Historical concrete checkpoint:

```text
branch: agent/codex/firetest-c-ffmpeg-full-phase-diagnostic
head:   cb3846bdbc2372150ba8164a667ef8ef7921cb7e
last head commit: 2026-08-23 — test(firetest): record phase c diagnostic evidence
```

The restored practical product-test frontier is:

```text
FireTest C
→ admit/configure FFmpeg as a governed AIpinho media-observation capability
→ run the FireTest product path
→ obtain evidence-backed Phase 1 diagnosis
→ execute/diagnose Phase 2 only if Phase 1 permits continuation
```

The purpose is diagnostic. A truthful block is an acceptable product-test result; success must not be manufactured.

### Music corpus update

The previous local music-folder location must no longer be assumed valid; it may have been moved or deleted.

Operator-provided expected location is approximately:

```text
D:\Rafa\músicas
```

This path is not yet host-verified evidence. Before the next FireTest execution, the governed local runner must discover/verify the actual path and bind the observed location into execution evidence.

The corpus consists of deliberately adversarial fake `.m4a` files. Production code must not treat the extension or filename as semantic media truth. `.m4a` may be routing/locator context; actual media identity/structure must come from governed observation evidence, including the planned FFmpeg capability where semantically applicable.

### FireTest re-entry invariants

- preserve historical FireTest branches, reports, artifacts, and evidence;
- do not infer `READY` from Control/H3 acceptance;
- do not hard-code `D:\Rafa\músicas`, Pinhoabacaxi, `.m4a`, row counts, filenames, or artifact names into production logic;
- FFmpeg must enter through the normal AIpinho capability/governance model rather than an ad-hoc subprocess bypass;
- Phase 2 must not pretend to execute if Phase 1 blocks;
- external Control evidence proves what Control executed/observed, not AIpinho semantic success;
- AIpinho Runtime/Validation/Completion/SpeakerTruth remain the authority for product/runtime truth.

The detailed technical context is maintained in:

```text
AIpinho_context_pack/docs/context/06_FIRETEST5.md
AIpinho_context_pack/docs/context/09_CURRENT_FRONTIER.md
AIpinho_context_pack/docs/context/current_state.json
```

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

The current H3 governed-engineering platform increases what Lúcio can safely operate through named capabilities; it is not generic permission for AIpinho to self-modify or execute unrestricted host commands.

## Current next step

1. Use H3-J progressive admission rather than jumping directly to full FireTest 5.
2. Verify the real corpus path on the host, expected approximately at `D:\Rafa\músicas`.
3. Verify the adversarial fake-`.m4a` corpus is present and characterize it without treating extension as Truth.
4. Reconcile the historical FireTest-C branch with current `main`; do not blindly revive old code.
5. Design/admit FFmpeg as a governed AIpinho capability with explicit applicability, execution, evidence, timeout and failure semantics.
6. Run a bounded product diagnostic to obtain Phase 1 evidence and conditional Phase 2 evidence.
7. Let the observed product result determine the next architectural wave; do not predeclare FireTest readiness.

If this file conflicts with Control `CURRENT_STATE.md`, Control wins for external execution/governance truth. AIpinho code/config and validated runtime evidence win for AIpinho product/runtime truth.
