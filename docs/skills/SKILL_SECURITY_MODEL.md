# Skill Security Model

Security guarantees:

- No manifest secret values are accepted.
- Unknown tools are rejected.
- Wildcard tool access is rejected.
- Raw/debug is hidden by default.
- Download tokens are never embedded in URLs.
- Source-readonly write declarations are rejected.
- Dangerous shell remains governed by Tool Gateway and policy.

The validator checks manifests before execution.

The executor checks capabilities before invoking tools.

The Tool Gateway checks policy before any effect.

Execution traces include evidence refs for audit.
