# Operational Runbook

## Health Checks

Use the backend health/config routes before a long run:

- core backend on `9088`;
- realtime on `9089` if enabled;
- artifact service on `9098` if enabled;
- monitor/supervisor on `9099`.
- semantic health on `/api/v1/health/semantics`.

If the mobile dashboard says `Backend: Online` but `Observability: Degraded`, distinguish service health from runtime state. Degraded observability can be caused by recent blocked/failed runs, active delegations, or stale field-trial evidence even when `/api/v1/health` is healthy.

## Safe Operation Flow

1. Create or select an agent session.
2. Send prompt.
3. Inspect timeline events.
4. Let policy decide allow, deny, approval or autoapproval.
5. Execute via Tool Gateway only.
6. Validate side effects.
7. Read Dashboard/Debugger for evidence.
8. Export artifacts/reports as needed.

## Internal Skill Flow

1. List available skills with `GET /api/v1/skills`.
2. Check health with `GET /api/v1/skills/health`.
3. Execute with `POST /api/v1/skills/{skill_id}/execute`.
4. Inspect `SkillExecutionResult` for `tool_invocation_ids`, `policy_decision_ids`, `validation_ids` and `output_artifact_refs`.
5. Inspect trace with `GET /api/v1/skills/executions/{skill_execution_id}/trace`.
6. Open mobile skills viewer at `GET /api/v1/mobile/view-model/skills`.

Skills are not a bypass. Effects must appear as Tool Gateway invocations with policy evidence.

## Field Trial State Hygiene

Before a formal field trial:

1. Export or copy runtime evidence stores to a debug bundle.
2. Run `POST /api/v1/runtime/hygiene/preview`.
3. Review candidates; no evidence should be deleted.
4. Run `POST /api/v1/runtime/hygiene/apply/{preview_id}` only if the preview is acceptable.
5. Confirm pending approvals are zero.
6. Confirm active delegations are zero.
7. Confirm old sessions are intentionally kept or archived.
8. Run `GET /api/v1/dashboard/multi-agent` and save the clean baseline.

Do not delete evidence blindly. Keep the backup path in the field-trial report.

## Emergency Handling

- Cancel active runs through the agent/session controls.
- Do not delete evidence directly.
- Use self-healing scan for stale/inconsistent runtime state.
- Use debug bundle export for diagnosis.

## RC3 Daily Use

1. Start AIpinho:
   `powershell -ExecutionPolicy Bypass -File scripts\start_aipinho.ps1`
2. Check status:
   `powershell -ExecutionPolicy Bypass -File scripts\status_aipinho.ps1 -WriteReport`
3. Run doctor when status is unclear:
   `powershell -ExecutionPolicy Bypass -File scripts\doctor_aipinho.ps1`
4. Prepare mobile pairing:
   `powershell -ExecutionPolicy Bypass -File scripts\prepare_mobile_pairing.ps1`
5. Open Launcher:
   `powershell -ExecutionPolicy Bypass -File scripts\open_launcher.ps1`
6. Backup before long field trials:
   `powershell -ExecutionPolicy Bypass -File scripts\backup_aipinho.ps1`
7. Restore preview only:
   `powershell -ExecutionPolicy Bypass -File scripts\restore_aipinho.ps1 -BackupZip <path>`
8. Stop AIpinho:
   `powershell -ExecutionPolicy Bypass -File scripts\stop_aipinho.ps1`

## Artifact Download

Artifacts must be downloaded by `artifact_id` through backend endpoints using an Authorization header. Do not place token values in URLs.

## Support Bundle Path

Use reports under `reports\health`, `reports\release`, `reports\regression` and backup archives under `backups`.
# Sprint 22: Smoke Lúcio Multimodal

1. Subir backend.
2. Abrir app mobile ou Launcher.
3. Criar sessão Lúcio.
4. Anexar screenshot ou log permitido.
5. Enviar pedido de diagnóstico.
6. Confirmar resposta humana sem raw.
7. Abrir Detalhes/Debugger.
8. Confirmar artifact refs, rota, risk level e eventos multimodais.
9. Se houver delegação, confirmar que Codex/AIpinho recebem contexto sanitizado.
# Project Profiles

Project Profiles are governed context records. Use them to select a project for AIpinho, Lúcio, Codex and Gemini without granting permissions directly.

Useful checks:

```powershell
Invoke-RestMethod http://127.0.0.1:9088/api/v1/projects/profiles/status
Invoke-RestMethod http://127.0.0.1:9088/api/v1/projects/profiles/doctor/health
Invoke-RestMethod http://127.0.0.1:9088/api/v1/mobile/view-model/projects
python tests\multi_agent\run_multi_agent_regression.py --project-profiles
```

Safety reminders:

- Profile selection is context, not authorization.
- Source-readonly workspaces must not receive writes.
- Tool Gateway, Policy Kernel and Approval remain final side-effect gates.
- Profiles containing secret-risk markers must be rejected or reviewed before use.

# Governed Sandbox

1. Check `GET /api/v1/sandbox/health`.
2. Create or select a sandbox workspace.
3. Create a sandbox task.
4. Use `/files/*`, `/shell/run` or the shared `sandbox_*` Tool Gateway tools.
5. Inspect `/tasks/{id}/trace`.
6. Export deliverables through `/artifacts/export`.
7. Use cleanup preview before cleanup apply.

Never use the sandbox cleanup flow to delete task traces, reports or final artifacts.

# Sandbox Project Factory Smoke

1. Restart backend after code changes.
2. Run `POST /api/v1/sandbox/project-factory/generate` with a project-generation prompt.
3. Confirm `zip_artifact_id`, `download_endpoint` and `requires_token=true`.
4. Confirm unauthorized download returns `401`.
5. Inspect ZIP entries when certifying a new template.
6. Treat `completed_with_warnings` as usable only when warnings are explicit and non-blocking.
