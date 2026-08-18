# AIpinho Philosophy

## Direction

AIpinho is not primarily a collection of scripts. It is an attempt to build a governed cognitive runtime that transforms language into action without pretending to know, execute, validate, or complete more than it actually has.

Guiding principle:

> AIpinho should grow by developing better internal representations of reality, not by accumulating patches.

Guiding question:

> How can the system understand better before acting?

## Philosophical chain

```text
language
→ meaning
→ intention
→ contract
→ intermediate representation / plan
→ governed execution
→ evidence
→ validation
→ completion
→ SpeakerTruth
→ user-facing operational truth
```

This is a cognitive/philosophical model. Concrete implemented runtime authorities and class/service names are documented separately in `05_RUNTIME_ARCHITECTURE_MAP.md`.

## Inviolable principles

- Do not invent.
- Do not hide failures.
- No execution without a contract.
- No validation without evidence.
- No success without SpeakerTruth.
- Candidate is not Truth.
- Derived is not observed.
- Unknown is not false.
- Similarity is not identity.
- Artifact existence is not semantic success.
- `result.json` existence is not completion.
- Path is a locator/evidence ref, not semantic identity.
- Filename is display/locator context unless governed evidence supports more.
- Extension is a routing hint, not semantic authority.
- Specific reason beats generic timeout.
- Every accepted run must terminalize explicitly.
- Bounded counters/digests/refs are preferred over repeated giant inline payloads.
- Repository state and knowledge artifacts must not claim mutually incompatible baselines.

## Terminality

Valid terminal states include completed, blocked, failed, and cancelled. A stall must become an explicit governed terminal state. A terminalized run should have exactly one terminal event.

## SpeakerTruth

SpeakerTruth is the final communication boundary. It must be able to say success, blocked, partial, insufficient evidence, or failed without pressure to make the outcome sound better.

## Knowledge honesty

Documentation must follow the same truth discipline as runtime output:

```text
document exists ≠ document is current
filename says canonical ≠ implementation confirms authority
conversation remembers it ≠ repository contains it
branch validated it ≠ main includes it
```

## Anti-patterns

Forbidden or strongly discouraged:
- FireTest-specific branches;
- path/filename/task-ID fixes;
- hidden bypasses;
- parallel escape flows;
- weakening validation to pass;
- increasing timeout instead of understanding cost;
- fixture-size thresholds in production;
- treating unit proof as public proof;
- treating one lucky run as determinism;
- treating a generated snapshot or historical document as current authority without verification.

## Motto

> Bloqueio honesto é melhor que sucesso falso.

## Complexity brake

Do not build a spaceship for a bicycle problem. But do not simplify away justified architecture merely because the correct solution is deeper than a patch.

