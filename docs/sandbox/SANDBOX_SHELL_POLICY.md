# Sandbox Shell Policy

Shell runs with `shell=False`, an argument vector and a cwd resolved inside the selected sandbox workspace.

Allowed categories:
- `readonly_shell`
- `test_shell`
- `build_shell`
- `package_shell`

Network, destructive, process-control, git-write and unknown shell are blocked. Commands have a timeout and return sanitized stdout/stderr, exit code, duration and evidence refs.
