# Engineering Constitution

Status: `GOVERNANCE_GUIDANCE`

Authority: subordinate to current code, active contracts/configuration, validated runtime evidence, and explicit human scope.

## Purpose

The Engineering Genome defines how this project should evolve. It is not a second runtime, a substitute for evidence, or a frozen catalogue of past solutions.

> Build systems whose complexity has an owner, whose decisions have provenance, whose truth has evidence, and whose evolution does not depend on remembering why a workaround existed.

## Core principles

### EG-01 — Evidence before claims

Observed, inferred, proposed, and unknown are different states. Tests, documentation, caches, filenames, extensions, model output, and prior conversations do not become runtime truth merely by existing.

### EG-02 — No contextual hardcode

A static value is legitimate when it encodes a real invariant. A decision that varies with mission, machine, capability, provider, environment, data, or user scope must be derived from those sources or from explicit policy/configuration.

Hardcode smell: a contextual decision frozen in code because one known case currently needs it.

### EG-03 — Single canonical authority
Multiple providers, adapters, fallbacks, workers, and implementations are allowed. Multiple authorities for the same truth are not. Every responsibility must have an identifiable canonical owner.

### EG-04 — No bypass; no shadow runtime

Fallbacks remain subordinate to the canonical path. Diagnostics may observe; compatibility layers may adapt; neither may silently become an alternative authority, lifecycle, policy engine, truth engine, or execution plane.

### EG-05 — Dynamic does not mean implicit

Dynamic resolution must expose enough provenance to explain the resolved value, source, scope, relevant context, validation, and lifetime. Greater adaptability requires greater observability.

### EG-06 — Information fidelity

Do not collapse information before the boundary where reduction is necessary. Preserve physical identity separately from display names, evidence separately from conclusions, unknown separately from false, and provenance separately from cached values.

### EG-07 — Semantic cache is an accelerator, never authority

Cache entries must declare what they cache, the semantic inputs that make them valid, provenance, invalidation conditions, and freshness rules. A cache hit cannot elevate confidence or authority beyond its source evidence.

### EG-08 — Responsibility has boundaries

Each substantial component should be able to state what it owns, consumes, produces, may do, and must not do. Convenience is not justification for leaking policy, persistence, UI, execution, or truth responsibilities across boundaries.

### EG-09 — Semantic testing
Tests must prove meaning, invariants, prohibited effects, and behavioral continuity—not merely that a function returned or a path executed. Important fixes require a regression that reproduces the prior behavior and proves the intended replacement behavior.

### EG-10 — Behavioral continuity and reversibility

Before structural change, characterize relevant existing behavior. Compare before/after evidence. Prefer changes that remain diagnosable and reversible when the cost is reasonable.

### EG-11 — Honest failure

Failure, blocked, partial, unsupported, unknown, and completed are meaningful outcomes. Do not weaken validation, hide errors, inflate timeouts, fabricate defaults, or report success merely to make a test or workflow green.

### EG-12 — Governed evolution, not dogma

The Genome constrains reasoning, not discovery. A justified exception is allowed when its scope, reason, consequences, evidence, and tests are explicit. Do not turn anti-hardcode principles into hardcoded architecture.

## Classification of values

| Class | Meaning | Preferred home |
|---|---|---|
| invariant | universally true inside the supported contract | code/schema/contract |
| policy | chosen behavior that may evolve | typed config/policy |
| capability | what the current environment can actually do | runtime discovery + bounded cache |
| context | mission, resource, repository, device, media, user scope | explicit context/contract |
| heuristic | evidence-weighted approximation | named policy + tests + telemetry |
The goal is not “zero constants.” The goal is zero accidental contextual authority.

## Healthy-change definition

A change is not complete merely because it compiles. Its scope should demonstrate, as applicable:

- intended behavior exists;
- relevant old behavior was characterized;
- no bypass or competing authority was introduced;
- contextual configuration remains contextual;
- information/provenance is preserved;
- responsibility boundaries remain coherent;
- semantic regressions exist;
- observed evidence supports the claim;
- affected documentation/current state were reconciled.
