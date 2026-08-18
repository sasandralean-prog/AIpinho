# Template Manifest Schema

Each template lives at:

`config/templates/registry/<template_id>/template.yaml`

Required identity fields:

- `template_id`
- `display_name`
- `slug`
- `version`
- `status`
- `category`
- `description`
- `generator_key`

Active templates must define:

- `required_files`
- `PROJECT_MANIFEST.json` in `required_files`
- `README.md` in `required_files`
- `validation_profile`

Operational fields:

- `supported_project_types`
- `supported_languages`
- `supported_platforms`
- `generated_assets`
- `artifact_policy`
- `risk_level`
- `required_capabilities`
- `compatible_skills`
- `compatible_autopilot_modes`
- `examples`

The validator intentionally fails active manifests that do not declare structural validation expectations.
