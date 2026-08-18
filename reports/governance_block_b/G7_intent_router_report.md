
# G7 Canonical Intent Router Report

- Generated UTC: 2026-06-26T09:00:00.641106+00:00
- Mode: consolidated canonical core, not route adapter
- Functional route rewire: not performed in this checkpoint


Checkpoint: `G7_CANONICAL_INTENT_ROUTER_READY`

Implemented:
- `CanonicalIntentRouter`
- `intent_normalizer`
- safe precedence: approval command, readonly/planning, workspace query, project bootstrap, patch/write, explicit session diagnostic, conversation.

Important note:
Regex is used only as signal collection inside the new canonical intent object. It is not wired as route-final authority yet.

Validation covered:
- readonly planning stays plan-only and does not create approval/write intent.
