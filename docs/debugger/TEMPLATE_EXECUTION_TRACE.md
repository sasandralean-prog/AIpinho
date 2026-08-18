# Template Execution Trace

Template metadata is attached to sandbox project generation results:

- `template_id`
- `template_version`
- `template_execution_id`

These fields appear in:

- `PROJECT_MANIFEST.json`
- `ProjectGenerationResult.metadata_sanitized`
- agent run metadata

Debugger surfaces should use these fields to show which declarative template produced a sandbox project.
