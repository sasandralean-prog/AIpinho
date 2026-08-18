# Skill Policy Model

Skills do not grant permissions.

They declare:

- capabilities required;
- tools allowed;
- tools denied;
- workspace constraints;
- artifact constraints;
- memory constraints;
- validation requirements;
- speaker truth policy.

Final authorization remains with:

- Workspace policy;
- Tool Gateway;
- Policy Kernel;
- Approval/AutoApproval;
- Validation Gate.

Examples:

- A reporting skill may call `generate_report` when `report_generate` is granted.
- A validation skill may call `validate` and must produce validation evidence.
- A patch skill must not apply a patch without preview/approval policy.
- A source-readonly workspace cannot receive writes from any skill.
