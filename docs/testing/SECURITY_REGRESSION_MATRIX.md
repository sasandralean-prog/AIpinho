# Security Regression Matrix

The security regression matrix lives at `tests/multi_agent/security_regression_matrix.yaml`.

Mandatory protections:

- Writes to source_readonly/protected/forbidden workspaces are blocked.
- Path traversal is blocked.
- Destructive, network, git write, process control and unknown shell are blocked by default.
- Secret-like values are redacted or blocked.
- Tokens must not appear in URLs.
- Raw/debug data is hidden by default.
- Debug bundles and reports must be sanitized.
- Self-healing must not delete evidence.

The quick suite validates representative policy and Tool Gateway paths.

