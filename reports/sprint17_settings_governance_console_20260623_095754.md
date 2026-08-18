# Sprint 17 - Settings UX Governance Console

Timestamp: 20260623_095754
Responsavel: Codex A
Projeto: AIpinho

## Objetivo

Expor a governanca configuravel no Settings Mobile e Launcher, consumindo as APIs oficiais de config governance, workspace registry, permission matrix, backups e workspace flow rules.

## Entregas

- Criado `GovernanceClient` no Launcher.
- Adicionado painel de governanca na aba Config do Launcher.
- Adicionado preview de flow plan no Launcher via `/api/v1/workspace-flows/plan`.
- Criado `GovernanceClient.kt` no Android.
- Adicionados botoes de leitura no Settings Mobile para Policy, Workspaces, Matrix, Flows, Mudancas e Backups.
- Estendido `ConfigMobileAggregator` para incluir cards humanizados de governanca, permission matrix e flow rules.

## Contrato UX

- UI nao edita config diretamente.
- UI consome endpoints oficiais.
- Mudancas reais continuam no fluxo `ConfigChangeRequest -> preview -> approval -> apply`.
- Tokens continuam redigidos/omitidos no modo normal.
- Flow rules sao visiveis e copiaveis; execucao depende de policy/approval.

## Arquivos criados/alterados

- `apps/launcher/ui/api/governance_client.py`
- `apps/launcher/ui/launcher_app.py`
- `apps/launcher/ui/tabs/settings_tab.py`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/network/GovernanceClient.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/SettingsScreen.kt`
- `src/aipinho/services/mobile_view_models/config_mobile_aggregator.py`

## Validacoes

- `python -m py_compile ...`: passed
- `python -m pytest tests\unit\test_workspace_flow_service.py tests\unit\test_mobile_view_model_service.py -q`: 12 passed
- App factory route registration: `workspace_flow_routes=10`, `config_routes=27`
- Android: `gradlew.bat -p apps/mobile/android :app:compileDebugKotlin`: BUILD SUCCESSFUL

## Handoff para UX

- Mobile Settings ja mostra governanca em cards/terminal.
- Launcher Config ja mostra health, effective policy, workspaces, matrix, flow rules, changes e backups.
- Proxima iteracao pode transformar campos de workspace/permissions em editores guiados, desde que continuem criando preview/diff e nao escrevam configs diretamente.

## Warnings

- A edicao rica de permissao/workspace ainda e backend-ready, mas a UI atual prioriza leitura, preview e trilha segura.
- QA visual manual em dispositivo nao foi executado nesta rodada.
- `git status` nao estava disponivel no diretorio atual porque `C:\Dev\AIpinho` nao foi detectado como worktree Git neste contexto.

## Veredito

READY_WITH_UX_FOLLOWUP
