# Mobile Dashboard Warning Closure — 2026-06-22 12:59:54

## Objetivo
Corrigir os avisos e falsos degradados observados no dashboard mobile/launcher sem hardcode, sem solução por caso específico e sem mascarar erros reais.

## Erros corrigidos
- `HTTP 0` no dashboard mobile: a causa era timeout na montagem pesada de `/api/v1/mobile/view-model/dashboard`, agravado por chamadas concorrentes na abertura da tela.
- `Inventario de endpoints: Degradado`: a rota usava `config/routes/routes.yaml` como fallback válido, mas classificava a ausência do inventário gerado como degradação.
- `Multi-Agent Dashboard: degraded` por `ValidationError`: o backend passou a emitir estado histórico para falhas terminais, mas o contrato mobile ainda não aceitava esse status.
- `Historico de bloqueios/falhas: healthy`: histórico de falhas estava sendo convertido em saúde atual para caber no schema.
- `Runs ativos` como warning operacional: atividade normal agora é `info`; alerta continua para approvals pendentes e falhas reais.
- Duplicação de approvals pendentes entre status de run e policy decision: deduplicado por run.

## Arquivos alterados
- `src/aipinho/services/agents/multi_agent_observability_service.py`
- `src/aipinho/services/mobile_view_models/dashboard_mobile_aggregator.py`
- `src/aipinho/services/mobile_view_models/mobile_endpoint_inventory_service.py`
- `src/aipinho/schemas/mobile_view_models/contracts.py`
- `config/runtime/multi_agent_observability_policy.yaml`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/network/MobileViewModelClient.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/DashboardScreen.kt`
- `apps/mobile/android/app/src/test/java/br/com/aipinho/mobile/DashboardPolishTest.kt`
- `tests/unit/test_mobile_endpoint_inventory_service.py`
- `tests/unit/test_runtime_state_hygiene_service.py`

## Correções de base
- Cache TTL configurável para dashboard multiagente, isolado por raízes reais dos stores.
- Timestamp do snapshot após a montagem completa, evitando cache já vencido.
- Timeout mobile dos view-models elevado para 30s.
- A tela Dashboard deixa de disparar uma segunda chamada pesada automaticamente no cockpit; inicializa com `status()` leve e mantém atualização manual do cockpit.
- `historical` adicionado ao contrato de status mobile.
- Endpoint inventory agora considera `config/routes/routes.yaml` fonte canônica válida quando o inventário gerado não existe.

## Fallbacks e mensagens de erro
- O fallback mobile agora mostra causa sanitizada (`timeout`, erro HTTP ou exceção redigida) em vez de só `HTTP 0`.
- Se o dashboard oficial falhar, o app consulta `/api/v1/mobile/view-model/status` e explicita que está em fallback.
- Falhas históricas continuam visíveis como histórico, não viram sucesso atual nem falha operacional ativa.

## Higiene de runtime aplicada
- Preview oficial: `cleanup_preview_6bcff1cc4a6e40c988e350dd38f972b4`.
- Aplicação oficial via `/api/v1/runtime/hygiene/apply/...`.
- 39 runs stale com mais de 24h foram marcados como `cancelled` com `error_code=stale_runtime_cleanup`.
- Evidências/eventos não foram apagados.

## Validações executadas
- `python -m py_compile` nos módulos Python alterados.
- `python -m pytest tests\unit\test_runtime_state_hygiene_service.py tests\unit\test_mobile_endpoint_inventory_service.py tests\integration\test_mobile_dashboard_view_model_api.py -q` → `13 passed`.
- Revalidação após status `historical` → `13 passed`.
- `python -m pytest tests\unit\test_runtime_state_hygiene_service.py tests\integration\test_mobile_dashboard_view_model_api.py -q` → `12 passed`.
- `apps\mobile\android\gradlew.bat -p apps\mobile\android testDebugUnitTest :app:assembleDebug` → `BUILD SUCCESSFUL`.
- Backend 9088 reiniciado por script canônico.
- APK instalado no celular físico `ZF5253V88S`.

## Evidência operacional
- 9088, 9080 e 9099 responderam health 200 em validações anteriores da rodada.
- Dashboard no celular físico exibiu:
  - `Status: Online`
  - `Core Backend esta online para o contrato /api/v1.`
  - `Core: 9088`
  - `Bootstrap: 9080`
  - `Monitor: 9099 (Online)`
  - `Historico de bloqueios/falhas: historical`
- Não apareceu `HTTP 0`.
- Não apareceu `Inventario de endpoints: Degradado`.

## Pendências legítimas
- `Realtime/SSE: unknown`: ainda precisa endpoint/health real dedicado ou contrato de heartbeat completo.
- `Approvals pendentes: pending`: há approvals pendentes reais; não foram negados automaticamente nesta rodada.
- `Legacy RAG: degraded`: estado intencional de governança, pois RAG legado segue apenas como referência histórica/diagnóstica.

## Veredito
`READY_WITH_KNOWN_OPERATIONAL_WARNINGS`

O dashboard deixou de mascarar timeout e deixou de classificar histórico como falha ativa. Restam avisos reais/contratuais que devem ser resolvidos por sprints próprios, não por maquiagem de status.
