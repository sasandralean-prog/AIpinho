# Configuration Guide

Use `.env.example` for documented placeholders. Real secrets belong in local untracked configuration only.

## Areas

- Agent registry: `config/agents/agent_registry.yaml`.
- Tool registry: `config/agents/tool_gateway_registry.yaml`.
- Tool workspaces: `config/agents/tool_gateway_workspaces.yaml`.
- Policy profiles: `config/agents/agent_policy_profiles.yaml`.
- Autoapproval policy: `config/policies/multi_agent_autoapproval_policy.yaml`.
- Block reason catalog: `config/policies/block_reason_codes.yaml`.
- Internal skill registry: `config/skills/registry/<slug>/skill.yaml`.
- Skill registry index: `config/skills/registry/skills_index.json`.

## Provider Keys

Never put provider keys in Android, launcher UI, reports, raw logs or committed files.

Provider keys belong in local environment variables or local untracked config. Use `scripts\dev\configure_agent_secrets.ps1` when available. Status and doctor scripts must report only whether keys are configured, never the values.

## Workspace Roles

- `source_readonly`: readable source, no writes.
- `target_mutable`: governed writes allowed by policy.
- `system_mutable`: maintenance only.
- `protected` / `forbidden`: side effects blocked.

## Internal Skills

Skills are local governed capability manifests. They declare capabilities, allowed tools, policies, validation and speaker-truth requirements. They do not grant permissions by themselves.

Useful checks:

```powershell
Invoke-RestMethod http://127.0.0.1:9088/api/v1/skills
Invoke-RestMethod http://127.0.0.1:9088/api/v1/skills/health
Invoke-RestMethod http://127.0.0.1:9088/api/v1/mobile/view-model/skills
python tests\multi_agent\run_multi_agent_regression.py --skills
```

Do not store secrets in skill manifests. Use environment/local secret configuration for credentials.

## Governed Local Sandbox

Sandbox policy lives in `config/sandbox/sandbox_policy.yaml`. The production root defaults to `C:\Dev\AIpinho\sandboxes`; tests may set `AIPINHO_SANDBOX_ROOT` and `AIPINHO_SANDBOX_DATA_ROOT`.

Do not broaden blocked shell patterns from application code. Changes to network, destructive commands, artifact limits and cleanup preview must be made in policy config and covered by regression tests.

## RC3 Scripts

- Start: `scripts\start_aipinho.ps1`
- Stop: `scripts\stop_aipinho.ps1`
- Status: `scripts\status_aipinho.ps1`
- Doctor: `scripts\doctor_aipinho.ps1`
- Launcher: `scripts\open_launcher.ps1`
- Mobile pairing: `scripts\prepare_mobile_pairing.ps1`
- Backup: `scripts\backup_aipinho.ps1`
- Restore preview: `scripts\restore_aipinho.ps1`

## Official Ports

- `9088`: core backend.
- `9089`: realtime/optional.
- `9098`: separated artifacts service when enabled.
- `9099`: monitor/supervisor control plane. It must not restart itself.

## Runtime Cleanup

Use runtime hygiene preview before field trials:

```text
POST /api/v1/runtime/hygiene/preview
```

Apply only after reviewing the preview. Do not use cleanup to hide failed runs or delete evidence.
# Sprint 22: Lúcio Multimodal

Configurações relevantes ficam em `config/agents/lucio_agent_policy.yaml`, bloco `multimodal`.

Campos principais:

- `enabled`
- `provider`
- `max_image_size_mb`
- `allowed_content_types`
- `store_images`
- `memory_write_default`
- `redaction_required`
- `delegation_enabled`

O backend também aceita variáveis de ambiente equivalentes em deployments futuros, sem expor secrets em frontend, logs ou relatórios.
