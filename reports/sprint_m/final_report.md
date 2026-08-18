# Sprint M — Real Delegation Runtime & Mandatory Delegation Contracts

## Veredito

REAL_DELEGATION_RUNTIME_READY

## Objetivo

Eliminar a possibilidade de um adapter externo afirmar que delegou uma tarefa sem existir contrato de runtime auditavel.

## Arquitetura implementada

- `DelegationDecisionEngine` decide entre `DIRECT_RESPONSE`, `DELEGATE`, `HYBRID`, `BLOCK` e `REQUIRES_APPROVAL`.
- `DelegationContract` persiste `delegation_id`, `parent_run_id`, `child_run_id`, executor, status, polling e evidencias.
- `DelegationPollingService` acompanha o child run pela Universal Task Session.
- `DelegationTruthValidator` bloqueia claims como "deleguei", "AIpinho respondeu" ou "executor retornou" sem `delegation_id`.
- Universal Task Session ganhou o estado publico `WAITING_DELEGATION`.
- O runtime profile `delegation_parent` foi adicionado por config, sem hardcode de provider.
- Rotas publicas neutras foram adicionadas em `/api/v1/external`.

## Endpoints novos

- `POST /api/v1/external/delegation-decisions`
- `POST /api/v1/external/delegations`
- `GET /api/v1/external/delegations`
- `GET /api/v1/external/delegations/{delegation_id}`
- `POST /api/v1/external/delegations/{delegation_id}/poll`

## Arquivos criados

- `src/aipinho/schemas/runtime/delegation_contract.py`
- `src/aipinho/services/runtime/delegation_decision_engine.py`
- `src/aipinho/services/runtime/delegation_truth_validator.py`
- `src/aipinho/services/runtime/delegation_polling_service.py`
- `config/runtime/profiles/delegation_parent.yaml`
- `tests/unit/test_real_delegation_runtime.py`
- `tests/unit/test_delegation_truth_validator.py`
- `tests/unit/test_child_run_creation.py`
- `tests/unit/test_polling_contract.py`
- `tests/unit/test_adapter_delegation_policy.py`
- `tests/unit/test_speakertruth_delegation.py`
- `tests/unit/test_runtime_delegation_events.py`

## Arquivos alterados

- `src/aipinho/services/external_collaboration_service.py`
- `src/aipinho/services/external_collaboration_store.py`
- `src/aipinho/services/external_adapter_registry.py`
- `src/aipinho/api/routers/external_collaboration_router.py`
- `src/aipinho/schemas/runtime/universal_task_session.py`
- `src/aipinho/schemas/runtime/task_run_state.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/runtime/runtime_profile_service.py`
- `config/runtime/task_runtime_policy.yaml`
- `config/runtime/task_run_lifecycle_policy.yaml`
- `config/runtime/task_run_event_policy.yaml`
- `apps/mobile/android/app/src/main/java/br/com/aipinho/mobile/ui/screens/AgentTabScreen.kt`
- `apps/launcher/ui/tabs/agent_desktop_tab.py`
- `tests/unit/test_universal_task_session_service.py`
- `tests/unit/test_external_collaboration_layer.py`
- `tests/integration/test_launcher_multi_agent_ui_contract.py`
- `apps/mobile/android/app/src/test/java/br/com/aipinho/mobile/MultiAgentMobileUiContractTest.kt`

## Testes executados

- `python -m py_compile` nos modulos Python alterados.
- `python -m pytest tests\unit\test_real_delegation_runtime.py tests\unit\test_delegation_truth_validator.py tests\unit\test_child_run_creation.py tests\unit\test_polling_contract.py tests\unit\test_adapter_delegation_policy.py tests\unit\test_speakertruth_delegation.py tests\unit\test_runtime_delegation_events.py tests\unit\test_universal_task_session_service.py tests\unit\test_external_collaboration_layer.py tests\unit\test_continuous_collaboration_runtime.py tests\integration\test_launcher_multi_agent_ui_contract.py -q`
- `.\gradlew.bat :app:testDebugUnitTest --tests br.com.aipinho.mobile.MultiAgentMobileUiContractTest --tests br.com.aipinho.mobile.ExecutorMessageCopyContractTest`
- `.\gradlew.bat :app:assembleDebug`
- `powershell -ExecutionPolicy Bypass -File scripts\package_launcher_desktop.ps1`

## Resultados

- Python focado: `35 passed`.
- Launcher/external focused: `11 passed`.
- Android unit focado: `BUILD SUCCESSFUL`.
- Android assembleDebug: `BUILD SUCCESSFUL`.
- Launcher build: `C:\Dev\AIpinho\dist\AIpinhoLauncher.exe`.
- APK instalado no dispositivo fisico `ZF5253V88S`.

## Smoke runtime

### Resposta direta

Prompt: `2+2`

Resultado:

- `mode=direct_response`
- `delegation_id=null`
- `child_run_id=null`
- `reason_code=simple_direct_query`

### Delegacao real

Prompt: `Pergunte a AIpinho quanto e 2+2`

Resultado:

- `delegation_id=delegation_b210e32256a841af9552510221bc81ba`
- `parent_run_id=task_run_f377849a8821472ab32e93ca9237a6f0`
- `child_run_id=task_run_3a4c51816ef54e6584068428293a7c59`
- parent session: `WAITING_DELEGATION`
- child session: `CREATED`
- polling: `polling_count=1`
- source: `universal_task_session`

## UX

- Launcher mostra `Delegation Timeline`.
- Mobile mostra bloco `Delegation`.
- Se nao houver `delegation_id`, a UI mostra `Resposta direta do Provider / Sem delegacao`.
- Se houver `delegation_id`, a UI mostra Delegation ID, executor, child run, polling, evidence e review.

## Speaker Truth

Provider que afirmar delegacao sem runtime evidence recebe:

- `SpeakerTruthViolation`
- `delegation_claim_without_runtime_contract`
- `review_loop`

## Riscos restantes

- O child run ainda nasce como TaskRun governado criado, mas execucao efetiva depende dos pipelines ja existentes para o operation/profile solicitado.
- O Decision Engine usa sinais configuraveis por metadata e heuristica conservadora; pode receber expansao futura por policy YAML.

