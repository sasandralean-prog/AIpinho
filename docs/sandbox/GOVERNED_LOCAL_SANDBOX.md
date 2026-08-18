# Governed Local Sandbox

The official local sandbox lives under `C:\Dev\AIpinho\sandboxes` by default. Tests and isolated deployments may override it with `AIPINHO_SANDBOX_ROOT`.

Inside a sandbox workspace, AIpinho agents may read, write, modify, copy, move, safe-delete, run classified shell commands, validate and export token-protected artifacts. Every operation records a task trace and a policy reason code.

The sandbox does not weaken normal workspace policy. Absolute paths, traversal, symlink/junction escape, external writes, network shell, destructive shell and git write remain blocked.

Canonical endpoints use `/api/v1/sandbox/*`. Agent execution may also use the registered `sandbox_*` tools through the shared Tool Gateway.

## Project Factory

Sprint 27 adds the Sandbox Project Factory for new project generation inside sandbox tasks.

Use:

- `POST /api/v1/sandbox/project-factory/classify`
- `POST /api/v1/sandbox/project-factory/generate`

The factory creates files only under sandbox task directories and exports deliverables through token-protected artifacts. External paths without a registered workspace are blocked with a safe sandbox alternative.
