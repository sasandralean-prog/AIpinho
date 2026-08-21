# Codex Prompt Style — AIpinho Mission Orders

Wave prompts are structured like engineering mission orders. The structure exists to prevent an implementation agent from optimizing the wrong boundary, hiding uncertainty, widening scope, or weakening governance to pass a fixture.

## Canonical anatomy

1. Wave title/frontier.
2. `ATENÇÃO CODEX`.
3. Factual baseline and repository target.
4. Public evidence.
5. Axioms.
6. Main objective.
7. Secondary objectives.
8. Ideal / acceptable / unacceptable outcomes.
9. Non-goals.
10. Competing hypotheses.
11. Disconfirming evidence.
12. Mandatory diagnostic.
13. Patch boundary.
14. Forbidden paths.
15. Observability.
16. Terminality / SpeakerTruth.
17. Unit tests.
18. Regression tests.
19. Generic scale validation.
20. Anti-hardcode audit.
21. Public diagnostic rerun.
22. Clean validation rerun.
23. Reports.
24. Issue policy.
25. Verdict enum.
26. Required final response.
27. Git state and exact target branch.
28. Short conceptual rule/metaphor.

Not every small task requires all 28 sections. Use the full mission-order form when architectural scope, proof, or agent handoff benefits from it. Do not turn structure into empty ceremony.

## Hypothesis pattern

```text
H-A — Linear scan per cell

Mechanism:
each cell walks the observation collection.

Supporting evidence:
cost grows with rows × columns × observations.

Disconfirming evidence:
direct/indexed lookups dominate and fallback scans are zero.

Admissible correction:
build a bounded immutable lookup index once per render.
```

## Non-goals protect architecture

Typical prohibitions:
- raise timeout;
- reduce corpus;
- skip rows;
- hardcode fixture values;
- branch on FireTest;
- remove provenance;
- bypass canonical service;
- treat artifact existence as success;
- confuse an engineering assistant with an internal runtime agent;
- update documentation to a state not yet present in the target branch.

## Tone

Direct, explicit, evidence-oriented. Useful labels include `OBSERVED`, `INFERRED`, `NOT YET PROVEN`, `REQUIRED`, and `FORBIDDEN`.

Humor/metaphors are welcome when they reinforce the boundary:
- "Do not widen the door before confirming it is still the same sofa."
- "If 55k cells cost four minutes, do not blame the comma."
- "The abacate should leave fingerprints at the scene."


## Current prompt warning

For the B3.6 frontier, mission orders must not authorize FireTest 5, C, ffprobe installation, budget increases, or corpus filtering before the public canary gate proves applicability-resolution capacity/admission behavior.
