# Skill Manifest Schema

Each skill manifest is stored under:

```text
config/skills/registry/<slug>/skill.yaml
```

Required governance fields:

- `skill_id`
- `display_name`
- `slug`
- `description`
- `version`
- `status`
- `category`
- `compatible_agents`
- `compatible_project_stacks`
- `required_capabilities`
- `allowed_tools`
- `denied_tools`
- `input_schema`
- `output_schema`
- `side_effects`
- `workspace_policy`
- `artifact_policy`
- `memory_policy`
- `validation_policy`
- `speaker_truth_policy`
- `risk_level`
- `approval_policy`

Valid statuses:

- `draft`
- `active`
- `disabled`
- `deprecated`
- `invalid`
- `experimental`
- `archived`

Validation blocks:

- secret-like values;
- wildcard tools;
- missing policy sections;
- unknown tools;
- `source_readonly_write`;
- side-effect patch apply without approval policy.

Deprecated and experimental skills may execute, but warnings are emitted.
