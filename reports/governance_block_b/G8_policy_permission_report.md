
# G8 Canonical Policy Permission Report

- Generated UTC: 2026-06-26T09:00:00.641106+00:00
- Mode: consolidated canonical core, not route adapter
- Functional route rewire: not performed in this checkpoint


Checkpoint: `G8_CANONICAL_POLICY_PERMISSION_READY`

Implemented:
- `CanonicalPolicyService`
- canonical vocabulary: `allowed`, `ask`, `denied`, `needs_clarification`, `invalid`, `expired`, `stale`.
- normalization from legacy terms such as `needs_approval`, `approval_required`, `waiting_input`, `blocked`.
- explicit `allowed` now wins over side-effect default ask.
- absent explicit decision for side effects defaults to `ask`.

Validation covered:
- `needs_approval`, `approval_required`, and `waiting_input` normalize to `ask`.
- `blocked` normalizes to `denied`.
