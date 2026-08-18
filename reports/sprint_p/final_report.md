# Sprint P — Dynamic Agent Ecosystem & Capability Marketplace

Veredito: `DYNAMIC_AGENT_ECOSYSTEM_READY`

## Objetivo

Transformar a AIpinho em um ecossistema modular onde o Planner e os clientes consultam agentes por capabilities, manifests, trust, health, custo, latencia e prioridade, sem conhecer providers especificos no orquestrador.

## Arquitetura implementada

- Criado schema canonico de marketplace de agentes:
  - `AgentManifest`
  - `AgentCapabilityDescriptor`
  - `AgentScope`
  - `AgentHeartbeat`
  - `AgentHealthSnapshot`
  - `CapabilityQuery`
  - `CapabilityMatch`
  - `CapabilityNegotiationResult`
  - `AgentMarketplaceSnapshot`
- Criado registry configuravel em YAML:
  - agentes estaticos oficiais;
  - capabilities;
  - runtime profiles;
  - trust level;
  - custo;
  - latencia;
  - prioridade;
  - restricoes;
  - politica de auto-disable.
- Criado runtime registry dinamico em:
  - `data/runtime/agent_marketplace_runtime.json`
- Criado `AgentMarketplaceService` com:
  - registro dinamico;
  - remocao dinamica;
  - heartbeat;
  - health snapshots;
  - degradacao;
  - auto-disable por falhas repetidas;
  - query por capability;
  - failover para agente saudavel;
  - snapshot para UI/API.
- `IntelligentPlannerService` agora seleciona executores por capability via marketplace.

## Endpoints criados

- `GET /api/v1/agent-marketplace/status`
- `GET /api/v1/agent-marketplace/agents`
- `GET /api/v1/agent-marketplace/health`
- `GET /api/v1/agent-marketplace/snapshot`
- `POST /api/v1/agent-marketplace/agents`
- `DELETE /api/v1/agent-marketplace/agents/{agent_id}`
- `POST /api/v1/agent-marketplace/agents/{agent_id}/disable`
- `POST /api/v1/agent-marketplace/agents/{agent_id}/heartbeat`
- `POST /api/v1/agent-marketplace/agents/{agent_id}/failure`
- `GET /api/v1/agent-marketplace/capabilities/{capability_id}`
- `POST /api/v1/agent-marketplace/query`
- `GET /api/v1/mobile/view-model/agents`

## UX

- Launcher:
  - nova aba `Agent Marketplace`;
  - snapshot de agentes;
  - health;
  - capabilities;
  - busca por capability;
  - heartbeat por agente;
  - raw governado oculto em collapsible.
- Mobile:
  - nova aba `Agentes`;
  - tela `AgentMarketplaceScreen`;
  - consome `MobileViewModelClient.agents()`;
  - payload vem do view-model canonico, sem progresso/status inventado.

## Evidencias

- Marketplace carregou `9` agentes oficiais.
- Capability marketplace descobriu `17` capabilities.
- Query `ocr` retornou `ocr_local`.
- Planner Android passou a gerar nodes com executores:
  - `planner_local`
  - `executor_local`
  - `debugger_local`
  - `vision_local`
  - `ocr_local`
  - `review_local`
  - `memory_local`
  - `supervisor_local`
  - `finalizer_local`

## Testes executados

- `python -m pytest tests/unit/test_agent_marketplace_service.py tests/unit/test_intelligent_planner_service.py tests/integration/test_launcher_multi_agent_ui_contract.py -q`
  - Resultado: `22 passed`
- `./gradlew.bat :app:testDebugUnitTest --tests br.com.aipinho.mobile.MobileViewModelClientTest`
  - Resultado: `BUILD SUCCESSFUL`
- `./gradlew.bat :app:assembleDebug`
  - Resultado: `BUILD SUCCESSFUL`
- Smoke FastAPI com `TestClient`:
  - `/api/v1/agent-marketplace/snapshot` => `200 ok`
  - `/api/v1/agent-marketplace/capabilities/ocr` => `200 matched ocr_local`
  - `/api/v1/mobile/view-model/agents` => `200 ok Agent Marketplace`
- Smoke backend vivo:
  - `/api/v1/health` => `ok`
  - `/api/v1/agent-marketplace/status` => `ok`

## Deploy local

- Launcher empacotado:
  - `C:\Dev\AIpinho\dist\AIpinhoLauncher.exe`
- APK debug compilado:
  - `C:\Dev\AIpinho\apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk`
- APK instalado no aparelho fisico:
  - device: `ZF5253V88S`
  - resultado: `Success`
- Backend 9088 reiniciado:
  - PID: `63380`
  - Local: `http://127.0.0.1:9088/api/v1/health`
  - Tailscale: `http://100.107.124.8:9088/api/v1/health`

## Riscos restantes

- O marketplace ainda registra agentes dinamicos em arquivo JSON local simples. Para volume maior, vale migrar para store transacional.
- Health endpoint externo por agente foi modelado no manifest, mas a coleta HTTP periodica ainda nao roda em background.
- O Planner ja seleciona por capability, mas alguns runtime profiles legados ainda existem como fallback historico fora do caminho principal.

## Conclusao

O Sprint P estabeleceu o Agent Registry + Capability Marketplace como fonte configuravel para selecao de agentes. A AIpinho agora consegue descobrir, registrar, degradar, desabilitar e selecionar agentes por capability, e o Planner passou a usar esse mecanismo sem branch por Gemini/Codex/provider.

Veredito final: `DYNAMIC_AGENT_ECOSYSTEM_READY`
