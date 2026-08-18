# Sprint K - Universal Approver & External Authority Layer

Veredito: UNIVERSAL_APPROVER_LAYER_READY

## Objetivo

Implementar uma camada governada para que humanos, adapters externos, agentes internos, service accounts e automations possam atuar como Universal Approvers sem se tornarem autoridades de execucao.

## Arquitetura Implementada

- AIpinho permanece como autoridade unica de execucao, planejamento, runtime, persistencia, validacao e Speaker Truth.
- Universal Approver registra quem decidiu, de onde veio a decisao, qual trust level/capability foi usado e qual assinatura auditavel foi gerada.
- A decisao textual de approver externo usa o mesmo ApprovalService existente; nao modifica store diretamente.
- A retomada da task continua pelo ApprovalTaskContinuationService e pelo runtime governado da AIpinho.
- Nenhuma logica especifica por provider foi adicionada em servico/config. Gemini e Codex aparecem somente em testes como approvers cadastrados dinamicamente.

## Arquivos Criados

- C:\Dev\AIpinho\src\aipinho\schemas\approvals\universal_approver.py
- C:\Dev\AIpinho\src\aipinho\services\approvals\universal_approver_service.py
- C:\Dev\AIpinho\src\aipinho\api\routers\universal_approver_router.py
- C:\Dev\AIpinho\config\governance\approval_capability_matrix.yaml
- C:\Dev\AIpinho\apps\mobile\android\app\src\main\java\br\com\aipinho\mobile\ui\screens\UniversalApproversScreen.kt
- C:\Dev\AIpinho\tests\unit\test_universal_approver_layer.py
- C:\Dev\AIpinho\reports\sprint_k\final_report.md
- C:\Dev\AIpinho\reports\sprint_k\final_report.json

## Arquivos Alterados

- C:\Dev\AIpinho\src\aipinho\schemas\approvals\approval_request.py
- C:\Dev\AIpinho\src\aipinho\schemas\approvals\approval_decision.py
- C:\Dev\AIpinho\src\aipinho\schemas\approvals\approval_event.py
- C:\Dev\AIpinho\src\aipinho\services\approvals\approval_service.py
- C:\Dev\AIpinho\src\aipinho\api\routers\__init__.py
- C:\Dev\AIpinho\apps\mobile\android\app\src\main\java\br\com\aipinho\mobile\MainActivity.kt
- C:\Dev\AIpinho\apps\mobile\android\app\src\main\java\br\com\aipinho\mobile\network\MobileViewModelClient.kt
- C:\Dev\AIpinho\apps\mobile\android\app\src\main\java\br\com\aipinho\mobile\ui\navigation\MainNavigationState.kt

## Endpoints Criados

- GET /api/v1/universal-approvers
- POST /api/v1/universal-approvers
- GET /api/v1/universal-approvers/mobile-view
- GET /api/v1/universal-approvers/approval-timeline
- GET /api/v1/universal-approvers/{approver_id}
- POST /api/v1/universal-approvers/approvals/{approval_id}/text-decision

## Testes e Evidencias

- python -m pytest tests/unit/test_universal_approver_layer.py -q
  - 10 passed
- python -m py_compile nos arquivos Python alterados do Sprint K
  - passed
- python -m pytest tests/unit/test_universal_approver_layer.py tests/unit/test_approval_service_expiry_listing.py tests/unit/test_hotfix_executable_approval_resume.py -q
  - 18 passed
- TestClient:
  - GET /api/v1/universal-approvers => 200 ok, 3 approvers
  - GET /api/v1/universal-approvers/mobile-view => 200 ok, cards universal_approvers e approval_timeline
- Android:
  - .\gradlew.bat :app:assembleDebug --console=plain => BUILD SUCCESSFUL
  - adb install -r app-debug.apk => Success
  - pacote br.com.aipinho.mobile abriu e processo ficou ativo no dispositivo fisico.

## Cobertura de Testes

- Human/External approval por contrato textual.
- Gemini approval via registro dinamico.
- Codex approval via registro dinamico.
- Capability denied.
- Trust level denied.
- Approval signature.
- Approval origin.
- Replay/double approval bloqueado.
- Approval expiration bloqueado.
- Unknown/disabled/revoked approver bloqueados.
- Timeline e mobile view-model usando a mesma fonte.

## Segurança

- External approver nunca executa arquivo, shell, patch ou runtime diretamente.
- external_may_execute permanece false.
- Approval authority sempre AIpinho.
- Signature inclui approval_id, approver_id, decision, policy snapshot hash, preview hash, text hash e authority.
- Capability/trust sao avaliados por categoria configuravel em approval_capability_matrix.yaml.
- Secrets nao sao armazenados nem expostos em schema, report ou UI.

## Riscos Restantes

- A UI mobile inicial exibe cards estruturados via terminal humanizado; pode evoluir para componentes visuais mais ricos.
- O build Android manteve dois warnings antigos de API depreciada para statusBarColor/navigationBarColor.

## Continuidade: Launcher/Desktop Alignment

- Criada aba desktop "Approvers" no launcher.
- Criado client desktop UniversalApproverClient usando os mesmos endpoints canonicos do backend.
- A aba desktop lista approvers, exibe approval timeline e permite registrar decisao textual por approval_id/approver_id/texto.
- O launcher nao recebeu branches por provider; Gemini/Codex continuam apenas identidades cadastraveis.
- Gerado executavel em C:\Dev\AIpinho\dist\AIpinhoLauncher.exe.
- Atualizada copia em C:\Users\rafae\Desktop\AIpinhoLauncher.exe.

Validacoes adicionais:

- python -m pytest tests/integration/test_launcher_multi_agent_ui_contract.py tests/e2e/test_mobile_cyberpunk_neon_feature_parity_flow.py tests/unit/test_universal_approver_layer.py -q
  - 17 passed
- .\gradlew.bat :app:testDebugUnitTest --tests br.com.aipinho.mobile.HorizontalTabsTest --console=plain
  - BUILD SUCCESSFUL
- .\gradlew.bat :app:assembleDebug --console=plain
  - BUILD SUCCESSFUL
- adb install -r app-debug.apk
  - Success
- powershell -ExecutionPolicy Bypass -File C:\Dev\AIpinho\scripts\package_launcher_desktop.ps1
  - C:\Dev\AIpinho\dist\AIpinhoLauncher.exe

## Conclusao

O Sprint K estabeleceu a camada Universal Approver sem bypass: qualquer participante autorizado pode emitir decisao textual auditavel, mas a AIpinho continua sendo a unica autoridade de registro, validacao, persistencia e retomada de execucao.
