# Mobile Dashboard Pending Approval / Warning Cleanup

Data: 2026-06-22 13:16:07

## Objetivo

Cancelar approvals pendentes autorizados pelo usuario e corrigir warnings residuais do dashboard mobile sem hardcode, sem mascarar falha real e sem apagar evidencias historicas.

## Acoes executadas

1. Consultado o dashboard multiagente vivo em `http://127.0.0.1:9088`.
2. Identificados 2 runs em `pending_approval`.
3. Cancelados via `AgentSessionKernelService.update_run`, usando lifecycle oficial:
   - `agent_run_d0de0a2b50274dc695b0c723df528f78`
   - `agent_run_eb55f3dfa2bf4b3dbd4411b4ed89e4bf`
4. Revalidado que `pending_approvals=0`.
5. Corrigido `DashboardMobileAggregator` para:
   - usar `RealtimeStatusService().status()` no card Realtime/SSE;
   - usar `MaintenancePlaneService().status()` no card Maintenance/Regression;
   - classificar Legacy RAG como `historical/info`, nao `degraded/warning`;
   - excluir cards `historical` da lista de warnings ativos.
6. Reiniciado backend 9088 pelo script canonico.

## Arquivos alterados

- `C:\Dev\AIpinho\src\aipinho\services\mobile_view_models\dashboard_mobile_aggregator.py`
- `C:\Dev\AIpinho\tests\integration\test_mobile_dashboard_view_model_api.py`

## Testes e validacoes

- `python -m py_compile src\aipinho\services\mobile_view_models\dashboard_mobile_aggregator.py`
- `python -m pytest tests\integration\test_mobile_dashboard_view_model_api.py tests\unit\test_realtime_status_service.py tests\unit\test_maintenance_plane_service.py tests\unit\test_runtime_state_hygiene_service.py -q`
  - Resultado: `14 passed in 16.23s`
- Restart backend:
  - `scripts\dev\stop_aipinho_9088.ps1`
  - `scripts\dev\start_aipinho_9088.ps1`
- GET `/api/v1/mobile/view-model/dashboard`
  - `state.status=healthy`
  - `state.warnings=[]`
  - `dashboard_realtime=healthy/success`
  - `dashboard_legacy_rag=historical/info`
  - `dashboard_maintenance=healthy/info`
- GET `/api/v1/dashboard/multi-agent`
  - `pending_approvals=0`
  - `active_runs=7`
  - falhas antigas permanecem como `historical`, nao como bloqueio ativo.
- GET `/api/v1/health`
  - `status=ok`

## Comportamentos alterados

- Realtime/SSE deixa de aparecer como `unknown` quando o service real esta disponivel.
- Maintenance/Regression deixa de aparecer como `unknown` quando `MaintenancePlaneService` responde.
- Legacy RAG continua visivel como diagnostico historico, mas nao contamina o estado ativo do dashboard.
- Warnings ativos deixam de incluir cards historicos.

## Riscos restantes

- Existem 7 runs ativas. Nao foram canceladas porque nao estavam em `pending_approval`; devem ser avaliadas por ciclo proprio caso virem stale.
- `multi_agent_failures` ainda existe como historico. Isso e esperado e preserva rastreabilidade.
- QA visual mobile fisico nao foi necessario porque a mudanca foi backend/view-model, mas pode ser repetido se a UI ainda mostrar cache antigo.

## Veredito

`READY`: approvals pendentes foram cancelados por fluxo oficial, dashboard vivo esta `healthy`, warnings ativos zerados, e os estados historicos foram preservados sem bloquear uso comum.
