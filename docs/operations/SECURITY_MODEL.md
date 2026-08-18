# Security Model

AIpinho uses capability, workspace and risk policies to preserve operational freedom without allowing silent unsafe actions.

## Mandatory Blocks

- Destructive shell.
- Git write/push by default.
- Network shell by default.
- Process control shell by default.
- Writes to source_readonly, protected or forbidden workspaces.
- Path traversal.
- Secret or token leakage.

## Visibility

- Normal mode is human and sanitized.
- Details mode may show identifiers and structured evidence.
- Raw/debug is hidden by default and must be explicitly requested.

## Artifact Downloads

Protected artifact downloads require Authorization headers. Tokens must not be embedded into URLs.

