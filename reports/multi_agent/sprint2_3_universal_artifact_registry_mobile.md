# Sprint 2+3 - Universal Artifact Registry + Mobile Agent Artifacts

Data: 2026-06-22

## Veredito

Sprint aprovado.

O backend agora possui um registry universal de artifacts capaz de expor artifacts por `artifact_id`, `agent_id`, `task_id` e `bridge_task_id`. A UX mobile das ilhas AIpinho, Lucio, Gemini e Codex passou a consumir o endpoint universal por agente/sessao e renderizar cards com origem, task, bridge task, status de validacao, avisos de missing/stale e download autenticado.

## Backend

Endpoints adicionados/fortalecidos:

- `POST /api/v1/artifacts`
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{artifact_id}`
- `GET /api/v1/artifacts/by-agent/{agent_id}`
- `GET /api/v1/artifacts/by-task/{task_id}`
- `GET /api/v1/artifacts/by-bridge-task/{bridge_task_id}`

O endpoint historico de download permanece em:

- `GET /api/v1/artifacts/{artifact_id}/download`

## Contrato de Artifact

Campos adicionados/reforcados:

- `source_agent`
- `owner_task_id`
- `bridge_task_id`
- `session_id`
- `local_path`
- `download_endpoint`
- `requires_token`
- `status`
- `validation_status`
- `provenance`
- `error_reason`

Regras aplicadas:

- artifact `ready` exige arquivo real e tamanho maior que zero, salvo `allow_empty` explicito;
- artifact com arquivo ausente ou vazio e status `ready` aparece como `missing` ou `stale`;
- token nao vai na URL;
- download continua exigindo token pelo client autorizado;
- artifacts de Tool Gateway sao agregados ao registry universal;
- artifacts delegados podem ser visiveis pela ilha de origem via `visible_to_agent_ids`.

## Mobile

Alteracoes principais:

- `AgentApiClient.artifacts(sessionId)` passou a chamar `/api/v1/artifacts/by-agent/{agent_id}?session_id=...`;
- `AgentArtifactPanel` mostra nome, tipo, tamanho, origem, task, bridge task, validacao, status e warnings;
- botoes incluidos: `Baixar`, `Copiar ID`, `Copiar caminho`;
- artifacts `missing` e `stale` nao sao tratados como sucesso visual;
- timeline das ilhas passou a destacar eventos importantes de artifact/delegation/approval/validation no modo normal.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/artifact_interaction_contracts.py`
- `src/aipinho/services/artifacts/artifact_interaction_core.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `src/aipinho/api/routers/artifact_router.py`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/network/AgentApiClient.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/components/AgentArtifactPanel.kt`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/AgentTabScreen.kt`
- `tests/integration/test_universal_artifact_registry_api.py`
- `tests/integration/test_mobile_agent_artifact_contract.py`

## Testes Executados

```powershell
python -m py_compile src\aipinho\schemas\artifacts\artifact_interaction_contracts.py src\aipinho\services\artifacts\artifact_interaction_core.py src\aipinho\services\artifacts\universal_artifact_registry_service.py src\aipinho\api\routers\artifact_router.py
```

Resultado: passou.

```powershell
python -m pytest tests\integration\test_mobile_agent_artifact_contract.py tests\integration\test_universal_artifact_registry_api.py tests\integration\test_artifact_api.py tests\integration\test_agent_tool_gateway_api.py -q --durations=10
```

Resultado: `15 passed in 33.76s`.

```powershell
.\gradlew.bat :app:assembleDebug
```

Resultado: passou.

## Observacoes

- A raiz `C:\Dev\AIpinho` nao esta registrada como repositorio Git no ponto inspecionado, entao o status de alteracoes foi documentado por escopo de arquivos tocados.
- Nenhuma API key, token ou segredo foi adicionado ao codigo, UI, logs ou reports.
- Nao houve hardcode de projeto, prompt, path ou agente especifico.

## Riscos Restantes

- QA visual em dispositivo real ainda pode validar espacamento final dos cards de artifact por densidade de tela.
- O registry universal agrega stores existentes; se um store legado registrar metadata incompleta, o card ainda aparecera, mas pode mostrar campos ausentes como `-`.

## Handoff

Codex B pode consumir:

- `GET /api/v1/artifacts/by-agent/{agent_id}?session_id={session_id}`
- `GET /api/v1/artifacts/by-task/{task_id}`
- `GET /api/v1/artifacts/by-bridge-task/{bridge_task_id}`

Para downloads, continuar usando:

- `GET /api/v1/artifacts/{artifact_id}/download`

com token no header, nunca na URL.
