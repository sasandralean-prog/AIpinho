# Workspace Profile Model

Workspace Profiles describe role and intended use for a project path. They do not authorize side effects by themselves.

Roles:

- `source_readonly`: readable source. Write denied. Read-only shell may be suggested, but Policy Kernel decides.
- `target_mutable`: governed write target. Preview, policy, approval and validation still apply.
- `artifacts`: generated artifacts.
- `reports`: generated reports.
- `logs`: logs and timeline exports.
- `backups`: rollback material.
- `temp`: temporary generated files.
- `protected`: read or write requires stricter policy.
- `forbidden`: access blocked.

Rules:

- Longest-path match wins.
- Deny overrides allow.
- Child overrides parent only when explicitly configured.
- Profile context cannot bypass Workspace Registry.

