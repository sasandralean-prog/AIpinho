# AIpinho RC3

RC3 packages AIpinho for local daily use.

## Added

- `scripts\start_aipinho.ps1`
- `scripts\stop_aipinho.ps1`
- `scripts\status_aipinho.ps1`
- `scripts\doctor_aipinho.ps1`
- `scripts\open_launcher.ps1`
- `scripts\prepare_mobile_pairing.ps1`
- `scripts\backup_aipinho.ps1`
- `scripts\restore_aipinho.ps1`
- first-run, pairing, launcher, backup and troubleshooting docs.

## Release Package

`dist\aipinho_local_rc3`

## Verdict

Final verdict is recorded in the RC3 operational readiness report.
# Sprint 22: Lúcio Multimodal Strong Mode

- Adicionado intake multimodal governado para Lúcio.
- Adicionado upload mobile de artifacts binários via base64.
- Adicionados contratos `LucioMultimodalMessage`, `LucioVisualArtifact` e `LucioRouteDecision` expandido.
- Adicionadas rotas de decisão para esclarecimento, bloqueio, delegação e pedido de melhor imagem.
- Adicionada suíte `--multimodal` no runner multiagente.
# Sprint 23 - Project Profiles

- Added governed Project Profiles as persistent context for project stack, workspaces, command recipes, validation profiles, artifacts and report namespaces.
- Added official APIs under `/api/v1/projects/profiles` and mobile selector `/api/v1/mobile/view-model/projects`.
- Propagated `project_profile_id` through delegation, agent runs, Tool Gateway invocations, events, artifacts and project-scoped memory candidates.
- Added secret-risk blocking for profiles and regression coverage through `--project-profiles`.

