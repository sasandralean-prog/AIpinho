# Skill Trace Model

Skill trace endpoint:

```text
GET /api/v1/skills/executions/{skill_execution_id}/trace
```

Trace includes:

- `skill_execution`;
- `evidence_refs`;
- `raw_default_visible=false`.

Related Tool Gateway events include:

- `tool_invocation_created`;
- `policy_check_started`;
- `policy_check_completed`;
- `artifact_created`;
- `tool_succeeded`;
- `tool_blocked`.

Skill-specific events include:

- `skill_execution_started`;
- `skill_deprecated_warning`;
- `skill_experimental_warning`;
- `skill_execution_completed`;
- `skill_execution_blocked`.
