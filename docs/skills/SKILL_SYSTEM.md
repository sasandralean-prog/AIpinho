# Internal Skill System

Sprint 24 introduced governed internal skills as reusable capability manifests.

Core rule:

- A skill declares intent, inputs, outputs, capabilities, tools and policies.
- A skill does not bypass Tool Gateway, Policy Kernel, Approval, Validation or Artifact lifecycle.
- Any effect is executed through `AgentToolGatewayService`.
- Raw/debug data is hidden by default.

Sandbox-aware skills may request registered `sandbox_*` tools. The skill still does not receive filesystem authority directly: Tool Gateway and Sandbox Policy resolve the workspace, path, command category, trace and artifact lifecycle.

Main services:

- `SkillManifestRegistryService`: loads, validates, lists and enables/disables manifests.
- `SkillManifestValidatorV2`: validates schema, tools, policies, secret risk and unsafe source-readonly writes.
- `SkillExecutionService`: creates or reuses an agent run and invokes allowed tools with skill metadata.

Main endpoints:

- `GET /api/v1/skills`
- `GET /api/v1/skills/health`
- `GET /api/v1/skills/categories`
- `POST /api/v1/skills/registry/reload`
- `POST /api/v1/skills/{skill_id}/enable`
- `POST /api/v1/skills/{skill_id}/disable`
- `POST /api/v1/skills/{skill_id}/execute`
- `GET /api/v1/skills/executions/{skill_execution_id}`
- `GET /api/v1/skills/executions/{skill_execution_id}/trace`
- `GET /api/v1/mobile/view-model/skills`

Seed skills:

- `internal.project_readonly_inventory`
- `internal.safe_markdown_report_generator`
- `internal.validation_runner`
- `internal.mobile_ux_static_audit`
- `internal.artifact_bundle_exporter`

The older preview/dry-run skill endpoints remain compatible.
## Sprint 27 Sandbox Project Skills

New sandbox skills are registry-declared and must execute through governed sandbox tools:

- `sandbox_android_kotlin_game_generator`
- `sandbox_asset_placeholder_generator`
- `sandbox_zip_exporter`
- `artifact_reliability_validator`

These skills do not grant external workspace writes. They are intended for sandbox project generation, placeholder asset creation, artifact export and artifact status validation.
