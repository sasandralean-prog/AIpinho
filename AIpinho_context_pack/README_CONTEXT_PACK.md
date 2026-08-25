# AIpinho Context Pack v0.4

A structured continuity layer for AIpinho.

Start at:
`docs/context/00_START_HERE.md`

This package separates philosophy, the Rafa + Lúcio working relationship,
engineering workflow, runtime architecture, FireTest 5 rules, roadmap and wave
history, current frontier, speculative ideas, handoff protocol, machine-readable
current state, and the external governed Control Plane used to bridge GitHub and
the local PC.

## v0.4 continuity checkpoint

Generated on 2026-08-25 after the reviewed Control Plane B1.0-D / B1.0-E / B1.0-E.1 integration and persistent self-hosted runner validation.

Control repository:
`sasandralean-prog/AIpinho-FireTest-Control`

Observed Control `main` after the final B1.0-E service integration and README refresh:
`fe9daa384ff83c0c417677f07d4bb317301f812e`

Control state:

```text
B1.0-D   = merged — governed test/profile/quick-validation expansion
B1.0-E   = merged — GitHub Actions result/artifact/rerun loop
B1.0-E.1 = merged — fail-closed result hardening + persistent service-runner fixes
runner   = aipinho-pc, Windows service, Automatic, Running
```

The persistent runner uses the official GitHub Actions Windows service mechanism under `\.\aipinho-runner`. Real service-backed run/rerun validation passed using run `32848578948`; attempt `2` produced artifact `9563333072` and recorded `is_rerun_attempt=true`.

This does **not** make the Control Plane a generic remote shell and does **not** change AIpinho runtime truth. Current Control authority remains named, schema-bounded capabilities with provenance and evidence.

Agreed Control roadmap:

```text
F   -> Governed Operation Submission / start loop
F.1 -> Lúcio-operated bounded FireTest profiles
G   -> Lúcio Authenticated Control Channel
G.1 -> authenticated lucio.shell authority
```

`F`, `F.1`, `G`, and `G.1` are planned work, not currently granted authority. FireTest is expected to need a larger bounded execution window; the planned normal FireTest ceiling is about 15 minutes rather than the current short workflow budget.

## Runtime frontier remains separate

The v0.4 Control Plane checkpoint does not supersede the current AIpinho runtime frontier recorded in `09_CURRENT_FRONTIER.md` and `current_state.json`.

The last Context Pack runtime checkpoint remains:

- `H1C0.R3.01 = OPEN`;
- latest reviewed slice in the pack: `H1C0.R3.01.B3.5`;
- latest reviewed verdict: `R3_01_B3_5_PUBLIC_CANARY_POST_COMPILE_STALL_FORENSICS_READY`;
- current specific blocker in that checkpoint: `POST_COMPILE_CAPABILITY_APPLICABILITY_RESOLUTION_STALLED`;
- next runtime frontier in that checkpoint: `H1C0.R3.01.B3.6 — Capability Applicability Resolution Capacity & Admission Control`;
- FireTest 5 remains `NOT_READY` at that recorded runtime checkpoint;
- C gate remains `CORRECTIVE_REQUIRED_BEFORE_C`.

Before runtime work, always re-read current Git/code/reports because the runtime branch may have advanced after this continuity update.

## v0.3 historical baseline

v0.3 represented the B3.5 forensic/report-correction state on branch:
`agent/codex/r3-01-b3-5-postcompile-stall-route-boundary`.

It moved the public canary from a generic post-compile stall to the specific applicability-resolution capacity frontier without claiming FireTest success.

## v0.2 historical baseline

v0.2 represented the R2.18/pre-R3 baseline:
- validated wave `H1C0.R2.18`;
- R2 exit verdict `H1C0_R2_READY_FOR_R3`;
- reconciliation of R2.18 into `main` at merge commit `bed449fa8d3e78670df2bdddf413da181add61ce`.

The pre-R3 repository/knowledge consistency gate remains historically closed:
`H1C0_PRE_R3_REPOSITORY_KNOWLEDGE_CONSISTENCY_READY`.

## Canonical path

The canonical directory is lowercase:

`AIpinho_context_pack/docs/context/`

Do not recreate the previous uppercase `docs/CONTEXT/` path.
