# Remocao da dependencia runtime OpenAI/Lucio

Timestamp: 2026-06-23 04:24:28

## Veredito

OPENAI_LUCIO_REMOVAL_READY

O Lucio deixou de ser agente ativo por padrao na AIpinho. O runtime OpenAI/Lucio esta desativado por configuracao, Gemini permanece como ilha textual ativa, AIpinho permanece como kernel de execucao local governada, e Codex permanece como ilha tecnica sob demanda.

## Problema corrigido

- O Lucio/OpenAI ainda podia aparecer como superficie ativa e gerar falhas de provider em conversa simples.
- O backend podia tratar OpenAI ausente como degradacao operacional, mesmo quando a decisao de produto era desativar Lucio.
- UX mobile/launcher ainda expunha Lucio como aba/agente ativo.

## Correcoes aplicadas

1. Configuracao
   - `OPENAI_ENABLED=false`
   - `LUCIO_ENABLED=false`
   - `LUCIO_PROVIDER=disabled`
   - `DEFAULT_TEXT_AGENT=gemini`
   - `.env.example` agora usa placeholders e nao exige chave OpenAI.

2. Backend
   - `LucioAgentConfigService` agora separa `enabled`, `openai_enabled`, `provider`, `visible_in_ux` e `allow_new_sessions`.
   - `LucioConfigStatus` agora retorna provider/status de forma estruturada sem exigir segredo.
   - `LucioAgentService` retorna `agent_disabled` sem iniciar provider, ferramenta, delegacao ou execucao local.
   - Rotas `/api/v1/lucio-agent/*` e `/api/v1/agents/lucio/chat` retornam bloqueio estruturado quando desativadas.
   - Registry de agentes deixa Lucio fora dos agentes ativos por padrao.
   - Policy de ilhas permite Gemini por padrao; Lucio so entra se explicitamente habilitado por env/config.

3. Launcher
   - Aba Lucio removida do launcher ativo.
   - Catalogo ativo do launcher contem Chat, Gemini e Codex.
   - Suporte compativel do cliente permanece somente para historico/codigo legado.

4. Mobile
   - Navegacao principal removeu a aba Lucio.
   - Teste de abas agora espera Dashboard, Chat, Gemini, Codex, Pipeline, Debugger 2.0 e Config.

## Arquivos alterados

- `src/aipinho/services/lucio_agent/lucio_agent_config_service.py`
- `src/aipinho/schemas/lucio_agent.py`
- `src/aipinho/services/lucio_agent/lucio_agent_service.py`
- `src/aipinho/api/routers/lucio_agent_router.py`
- `src/aipinho/api/routers/hybrid_agent_router.py`
- `src/aipinho/services/agents/agent_profile_registry_service.py`
- `src/aipinho/services/agents/hybrid_execution_policy_service.py`
- `config/agents/lucio_agent_policy.yaml`
- `config/agents/agent_registry.yaml`
- `config/agents/hybrid_execution_policy.yaml`
- `.env.example`
- `apps/launcher/ui/launcher_app.py`
- `apps/launcher/ui/agent_catalog.py`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/navigation/MainNavigationState.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/MainActivity.kt`
- `tests/unit/test_lucio_agent_service.py`
- `tests/integration/test_lucio_agent_api.py`
- `tests/integration/test_agent_bridge_sprint6_7_hybrid_islands.py`
- `tests/integration/test_multi_island_sprint10_11_routing.py`
- `tests/unit/test_agent_session_kernel_service.py`
- `tests/unit/test_launcher_multi_agent_client.py`
- `tests/integration/test_launcher_multi_agent_ui_contract.py`
- `tests/multi_agent/multimodal/test_lucio_multimodal_regression.py`
- `apps/mobile/android/app/src/test/java/br/com/aipinho/mobile/HorizontalTabsTest.kt`

## Evidencias de teste

- `python -m py_compile ...`: passou.
- `python -m pytest tests/unit/test_lucio_agent_service.py tests/unit/test_agent_session_kernel_service.py -q`: 28 passed.
- `python -m pytest tests/integration/test_lucio_agent_api.py tests/integration/test_multi_island_sprint10_11_routing.py tests/integration/test_agent_bridge_sprint6_7_hybrid_islands.py -q`: 16 passed.
- `python -m pytest tests/unit/test_launcher_multi_agent_client.py tests/integration/test_launcher_multi_agent_ui_contract.py -q`: 9 passed.
- `python -m pytest tests/multi_agent/multimodal/test_lucio_multimodal_regression.py -q`: 4 passed.
- `./gradlew.bat testDebugUnitTest --tests br.com.aipinho.mobile.HorizontalTabsTest`: BUILD SUCCESSFUL.

## Smoke

Com `OPENAI_ENABLED=false`, `LUCIO_ENABLED=false`, `LUCIO_AGENT_ENABLED=false`, `LUCIO_PROVIDER=disabled`:

- `GET /api/v1/lucio-agent/health` retornou `status=disabled_by_config`, `provider=disabled`.
- `POST /api/v1/lucio-agent/sessions` retornou `status=blocked`, `reason_code=agent_disabled`.
- `POST /api/v1/agents/lucio/chat` retornou `status=blocked`, `reason_code=agent_disabled`.
- `GET /api/v1/agents?enabled=true` retornou `aipinho`, `codex`, `gemini`, sem `lucio`.

## Seguranca

- Nenhuma chave OpenAI foi adicionada ao codigo.
- Android e Launcher nao recebem chave OpenAI.
- Rotas Lucio desativadas nao chamam provider externo.
- Bloqueio estruturado informa `local_execution_started=false`, `tool_invoked=false`, `delegation_started=false`.

## Compatibilidade preservada

- Modulos e rotas historicas do Lucio permanecem para leitura/compatibilidade.
- Testes multimodais do Lucio continuam possiveis quando o agente e explicitamente habilitado por env.
- Historico antigo pode continuar existindo, mas novo chat Lucio fica bloqueado por padrao.

## Riscos restantes

- `InterpretationAgentService` ainda contem caminho compat para Lucio, mas a policy padrao e o router hibrido impedem uso ativo quando desativado.
- `apps/mobile/.../LucioAgentScreen.kt` permanece como arquivo legado nao roteado.
- Warnings Android existentes sobre `statusBarColor` e `navigationBarColor` sao de API de UI e nao bloqueiam este hotfix.

