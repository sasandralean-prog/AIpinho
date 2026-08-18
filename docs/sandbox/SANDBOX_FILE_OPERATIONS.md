# Sandbox File Operations

Canonical operations:
- read, write, append and modify;
- mkdir and list;
- copy and move;
- delete-safe.

All paths are relative to a registered sandbox workspace. `delete-safe` moves content to `sandboxes/trash`; it does not permanently erase evidence. Hash-aware modification is available through `expected_hash`.

Blocked operations return a structured reason code such as `sandbox_path_traversal_blocked` or `sandbox_escape_blocked`.
