# Freedom Regression Matrix

The freedom regression matrix lives at `tests/multi_agent/freedom_regression_matrix.yaml`.

Purpose: prevent the policy system from becoming so restrictive that safe work becomes impossible.

Protected expectations:

- Read/search in an allowed workspace should autoapprove.
- Artifact upload/download should autoapprove.
- Validation and report generation should autoapprove.
- Create/modify in target_mutable can autoapprove in governed autorun or power user modes.
- Readonly/test/build/package shell categories can proceed when policy allows.
- Memory absence or stale memory should warn, not block safe execution.

Security still wins for destructive, unknown, forbidden or secret-bearing operations.

