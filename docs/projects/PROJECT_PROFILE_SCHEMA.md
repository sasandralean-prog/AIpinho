# Project Profile Schema

Required concepts:

- `project_id`: stable identifier.
- `display_name`: human label.
- `slug`: file-safe profile name.
- `profile_status`: `draft`, `active`, `needs_review`, `invalid`, `stale` or `archived`.
- `root_ref`: sanitized root reference.
- `stack`: detected stack such as `android_gradle`, `python`, `node`, `mixed` or `unknown`.
- `workspace_profiles`: source/target/artifact/report/log workspace context.
- `command_profiles`: governed command recipes.
- `validation_profiles`: validation sequences and evidence rules.
- `memory_namespace`, `artifact_namespace`, `report_namespace`: project-scoped storage labels.

Forbidden content:

- API keys.
- Tokens.
- Passwords.
- Private keys.
- Raw logs.
- User-specific one-off routing rules.

Profiles are YAML files under `config/projects/profiles` with `PROJECT_PROFILES_INDEX.json` as the read index.

