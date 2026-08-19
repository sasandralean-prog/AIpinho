---
name: aipinho-wave
description: Use for bounded AIpinho engineering waves that need diagnosis, evidence, tests, reports, and an exact verdict.
---

# AIpinho Wave

Use this skill for ordinary AIpinho engineering waves.

## Flow

```text
baseline
-> observed frontier
-> competing hypotheses
-> mandatory diagnostic
-> evidence
-> root-cause classification
-> bounded patch
-> focused tests
-> regressions
-> required public/local validation
-> reports
-> issue register
-> verdict
-> next frontier
```

## Proof Levels

State the highest proof actually observed:

- `static_repository`
- `unit`
- `regression`
- `cloud_integration`
- `local_integration`
- `diagnostic_public`
- `final_public`

Do not upgrade proof level by inference.

## Rules

- Start from current Git state and current authority docs.
- Do not widen runtime scope without evidence.
- Do not patch before the failing boundary is mapped.
- Keep P0/P1/P2/P3 issue state explicit.
- Preserve terminality, evidence, validation, completion, and SpeakerTruth.
- Do not report FireTest or runtime success unless public evidence proves it.
