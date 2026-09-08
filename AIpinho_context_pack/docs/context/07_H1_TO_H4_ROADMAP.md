# H1 to H4 Roadmap — Strategic Horizons

## Purpose

The H1–H4 labels in this document are **AIpinho strategic maturity horizons**. They organize objectives, architectural ideas, and product directions by planning distance and maturity. They are not patches, release versions, individual corrective waves, or evidence that every item inside a horizon is implemented.

The horizons answer a planning question:

> What kind of capability and maturity should AIpinho grow toward from the near term to the long term?

They do not replace current runtime wave identifiers such as `H1C0.R3.01.B3.5`, issue IDs, FireTest gates, commits, or validated reports.

## Mandatory namespace rule

Do **not** confuse these strategic horizons with the similarly named Control Plane tranches.

```text
AIpinho Horizon H1 / H2 / H3 / H4
    = strategic product/maturity planning categories
    = objectives and ideas organized from near-term to long-range
    = not patches or specific implementation updates

CONTROL-H1 / CONTROL-H2 / CONTROL-H3
    = concrete implementation/validation tranches in AIpinho-FireTest-Control
    = Lúcio Shell / external Control Plane engineering governance
    = separate namespace with separate evidence and lifecycle
```

The shared numbers are a naming coincidence/history artifact. There is **no semantic equivalence** between `Horizon H1` and `CONTROL-H1`, between `Horizon H2` and `CONTROL-H2`, or between `Horizon H3` and `CONTROL-H3`.

Never infer that completing a Control tranche advances an AIpinho strategic horizon, and never infer that a Horizon objective grants Control authority.

## Planning interpretation

### Horizon H1 — Reliable Engine and Evidence

Planning distance: **near term / foundational maturation**.

Themes include:
- reliable governed execution;
- explicit contracts and policy boundaries;
- observation and evidence acquisition;
- terminality and truthful failure;
- artifact/evidence provenance;
- deterministic validation;
- SpeakerTruth and user-facing operational truth;
- closing structural runtime bottlenecks exposed by adversarial tests.

H1 is a strategic bucket. Concrete work inside it still needs its own wave, branch, tests, evidence, and verdict.

### Horizon H2 — Tool Intelligence and Operations

Planning distance: **medium term**.

Themes include:
- richer governed tools and capabilities;
- capability discovery, applicability and admission;
- better operational planning and tool selection;
- stronger external observation/perception;
- bounded integrations and dependency/tool lifecycle;
- reusable operational intelligence rather than fixture-specific flows.

H2 is not `CONTROL-H2`. Control may already have a tranche named CONTROL-H2 while AIpinho Horizon H2 remains a broader product-planning category.

### Horizon H3 — Agentic Collaboration and Initiative

Planning distance: **medium-to-long term**.

Themes include:
- governed collaboration among internal/external agent roles;
- delegated initiative with explicit authority;
- persistent collaboration without confusing continuity with authorization;
- task decomposition and cooperation;
- stronger planning/reflection loops;
- human-visible reasoning/evidence handoffs where appropriate.

H3 is not `CONTROL-H3`. The Control Plane currently has a mature CONTROL-H3 engineering-governance stack, but that does not mean AIpinho's strategic Horizon H3 is complete.

### Horizon H4 — Distributed / Selective Evolution

Planning distance: **long range / exploratory**.

Themes may include:
- distributed cognition/execution;
- selective self-improvement under governance;
- architectural evolution with explicit evidence and rollback boundaries;
- multi-node or multi-environment cooperation;
- research ideas that should remain speculative until concrete contracts and evidence exist.

H4 is deliberately less committed than near-term horizons. It is a place to preserve direction without pretending a roadmap idea is current runtime authority.

## Relationship to current runtime work

The strategic horizons coexist with concrete engineering identifiers. For example:

```text
Horizon H1
  broad planning category

H1C0.R3.01.B3.x
  concrete runtime/wave lineage with specific evidence

CONTROL-H3-J
  separate external Control Plane tranche governing progressive FireTest re-entry
```

These labels must be read in their full namespace, not by the number alone.

## Current planning posture — 2026-09-07

AIpinho is still dominated by Horizon-H1 concerns: truthful governed execution, evidence, observation, capability admission, terminality, and product-level FireTest diagnosis. That does not make every H1 idea a current patch, nor does it imply later H2/H3/H4 work is authorized.

The immediate operational work is a fresh governed FireTest re-entry from the clean 2026-09-07 baseline. Its result should determine the next concrete runtime wave. Strategic horizons remain guidance above those waves, not substitutes for them.

## Rule of promotion

An idea moves from Horizon planning into implementation only when it has:

```text
clear problem / objective
→ architectural owner
→ explicit contract or design boundary
→ bounded implementation scope
→ validation plan
→ evidence
→ truthful verdict
```

Until then, it remains planning context.
