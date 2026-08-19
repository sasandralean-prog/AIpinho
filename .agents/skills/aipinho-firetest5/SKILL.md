---
name: aipinho-firetest5
description: Use when planning, running, or interpreting FireTest 5 validation without turning the fixture into architecture.
---

# AIpinho FireTest 5

FireTest 5 is an adversarial validation fixture. It is not the product
architecture.

## Required Discipline

- Do not create production branches for Pinhoabacaxi, local paths, artifact
  names, extensions, or fixture row counts.
- Do not relax validation, completion, SpeakerTruth, metadata sufficiency, or
  phase dependency to make a run pass.
- Do not treat artifact existence, result existence, or CSV existence as
  semantic success.
- Keep A+B semantic comparisons when determinism matters.
- Preserve terminality: final result, finished_at, exactly one terminal event.
- Phase 2 and later must not run after a blocked Phase 1.
- Cloud environments cannot claim local FireTest proof unless they observed the
  real required local environment.

## Reporting

Report the exact observed blocker, reached stages, skipped stages, endpoint
health, SpeakerTruth, queue/runtime health, and proof level.
