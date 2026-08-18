# AIpinho Engineering Workflow

## Default wave loop
```text
baseline
→ observed frontier
→ competing hypotheses
→ mandatory diagnostic
→ root-cause classification
→ bounded patch
→ focused tests
→ regressions
→ public diagnostic rerun
→ public clean validation rerun
→ issue register
→ verdict
→ next frontier
```

## Diagnose before patch
Do not ask first: "what patch will make the test pass?"

Ask: "what boundary is actually failing, and what evidence would prove or disprove each plausible cause?"

## Priority policy
### P0
Truth, governance, terminality, corruption, false-success, authority confusion.

### P1
Structural runtime blockers, complexity failures, generic capability/binding defects, nondeterminism.

### P2
Observability/schema/projection problems that affect diagnosis or validation.

### P3
Cosmetic/report formatting; may be deferred.

## Wave boundary
A wave has an architectural owner. Internal iteration is allowed when the next blocker belongs to the same boundary:
```text
diagnostic → patch A → rerun → related blocker → patch B
```
Do not chase unrelated future frontiers forever inside one wave.

## Public proof
Distinguish:
- unit validated;
- regression validated;
- diagnostic public reached;
- clean public validation;
- final public proof.

Never say "publicly validated" when only a unit test exercised the behavior.

## A+B
When determinism matters, compare input identity, projected identity, row model identity, render order, schema digest, cardinality, semantic outcome, and terminal semantics. Wall time may differ; semantics should not.

## Git protocol
```text
sync baseline
→ create wave branch
→ implement
→ tests
→ public validation
→ reports
→ README status update
→ commit
→ push
```

## Issue schema
Prefer separate dimensions:
```text
evidence_status:
  not_proven | probable_with_evidence | proven

resolution_status:
  open | fixing | fixed | validated | deferred

validation_scope:
  none | unit | regression | diagnostic_public | final_public
```

A proven bug is not automatically a resolved bug.

## End-of-wave
State exact verdict, FireTest status, root cause, changes, proof level, open P0/P1/P2, terminality, SpeakerTruth, next frontier, and Git branch/commit/push state.
