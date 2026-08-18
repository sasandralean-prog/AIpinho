# Template System

Sprint 31 introduced a declarative template catalog for sandbox project generation.

The official flow is:

1. User prompt enters SandboxProjectFactory.
2. The factory infers a generic project type.
3. TemplateRegistryService selects a TemplateManifest from `config/templates/registry`.
4. TemplateExecutionService renders files through a registered generator key.
5. SandboxProjectFactory writes files through the governed Tool Gateway.
6. Structural validation checks manifest `required_files`.
7. A sandbox zip artifact is exported with token-protected download metadata.

Templates are config-first. Code owns reusable generators; config owns which generators are active, supported project types, required files, risk, capabilities, examples, and validation profile.

Current catalog:

- `android_kotlin_game`
- `android_kotlin_app`
- `python_cli`
- `python_fastapi`
- `static_web`
- `docs_pack`
- `mobile_component_demo`
- `launcher_tool_demo`
- `generic_files`

Remote downloads are not part of template execution.
