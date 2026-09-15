# AIpinho Context Pack v0.5 — consolidated runtime checkpoint

A structured continuity layer for AIpinho. Start at `docs/context/00_START_HERE.md`.

## Current checkpoint — 2026-09-15

AIpinho runtime implementation baseline: `6126a73a9ddfc054fe527174fe4df16740b9d1e0`.

```text
Semantic Sprints 0–9 = integrated
runtime + roles consolidation = COMPLETE / VALIDATED
FireTest consolidation = all six phases reached
Phase 1 = partial / limited-use / no success claim
Phases 2–6 = completed
timeline gaps/duplicates = 0/0
role pipeline = executed in 6/6 TaskRuns
Runtime Doctor = completed all six phases
focused regression after reboot = 174 passed / 0 failed
workspace/corpus mutations = 0/0
```

The older 06/09 `BLOCKED_PRE_TASK`, 07/09 `NOT_READY`, and first 15/09 `PARTIAL` checkpoints remain historical evidence, not the current runtime state.

## Five canonical authorities

1. Human operator.
2. Trusted dispatcher.
3. Local execution broker.
4. AIpinho runtime.
5. Evidence/result layer.

Dispatcher/broker logic validates and routes fixed capabilities; it does not interpret user meaning or become a second AIpinho runtime.

## Current runtime rule

One canonical product execution line owns TaskRun lifecycle and final truth. Roles/models are subordinate TaskRuntime children. Runtime Doctor is diagnostic. Runtime V2 planner/dispatcher/contracts are compatibility/introspection.

## Genome v2

`genome/` was regenerated from the GitHub `main` recursive tree and matching local Git object at the consolidated baseline.

Key entrypoints:

- `genome/00_manifest.json`
- `genome/reports/genome_summary.md`
- `genome/reports/github_folder_audit_20260915.md`
- `docs/context/05_RUNTIME_ARCHITECTURE_MAP.md`

Genome is generated orientation, not runtime authority.

## Strategic horizon terminology

`Horizon H1/H2/H3/H4` are AIpinho strategic maturity horizons. `CONTROL-H1/H2/H3` are separate external Control Plane implementation/validation tranches. Their numbers are not semantically mapped.

## Cross-repository rule

AIpinho runtime truth comes from AIpinho code/config/contracts and validated AIpinho evidence. The external Control Plane proves only the bounded operations it authenticates/executes/observes/packages. Envelope/request repositories are transport/intake unless their own authenticated boundary proves more.

Reobserve external repository heads before live work; this pack intentionally does not freeze their SHA as permanent current truth.

## Current frontier

There is no open P0/P1 carried forward from the runtime/roles consolidation FireTest wave.

Near-term engineering should:

- evolve only through the single canonical TaskRuntime;
- keep roles/models contract-bound and non-authoritative;
- clean up compatibility surfaces only with evidence-backed migration;
- preserve edge-local semantic admission and RuntimeTruth-bound public claims;
- refresh Genome/current-state docs after architecture-changing waves.

Deferred: Windows subprocess `cp1252/.m4a` media-probe reader issue.

## Historical baselines

Older Context Pack versions remain useful for rationale, Control progression and FireTest archaeology. Current code/config/live evidence always wins over those snapshots.
