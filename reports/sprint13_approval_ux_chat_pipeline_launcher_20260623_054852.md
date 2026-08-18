# Sprint 13 — Approval UX no Chat, Pipeline e Launcher

Timestamp: 20260623_054852
Projeto: AIpinho
Root: C:\Dev\AIpinho

## Veredito
APPROVAL_UX_READY_WITH_WARNINGS

## Base usada
Sprint 12 backend foundation: funcional em testes focados. ApprovalRequest, ApprovalDecision, endpoints approve/deny, safe batch, task resume e denial cancellation estão implementados.

## Alterações Mobile
- PipelineClient agora consome endpoints de pending/task approvals, deny e safe batch.
- Pipeline mobile ganhou botões:
  - Aprovar
  - Negar
  - Aprovar seguras
  - Negar seguras
  - Cancelar task
- Chat mobile ganhou ações diretas para approval encontrado no payload humanizado:
  - Aprovar approval
  - Negar approval
  - Aprovar seguras
- As ações chamam backend oficial e fazem refresh do view-model; a UI não decide policy.

## Alterações Launcher
- PipelineClient ganhou pending approvals e approve/deny safe batch por task.
- PipelineTab renderiza um Approval Center antes dos cards de task.
- Approval Center mostra approval_id, task/run, operação, risco, workspace, paths, commands e expiração.
- Approval Center oferece Aprovar, Negar, Aprovar seguras e Negar seguras.

## Endpoints consumidos
- GET /api/v1/approvals/pending
- POST /api/v1/approvals/{approval_id}/approve
- POST /api/v1/approvals/{approval_id}/deny
- POST /api/v1/tasks/{task_id}/approvals/approve-safe-batch
- POST /api/v1/tasks/{task_id}/approvals/deny-safe-batch

## Testes executados
- python -m py_compile nos arquivos Python alterados.
- ./gradlew.bat :app:compileDebugKotlin
- ./gradlew.bat :app:testDebugUnitTest --tests "br.com.aipinho.mobile.*Chat*" --tests "br.com.aipinho.mobile.*Pipeline*"
- python -m pytest tests\\unit\\test_governed_approval_continuation.py tests\\unit\\test_approval_preview_lifecycle.py tests\\unit\\test_approval_policy_service.py tests\\unit\\test_task_queue_service.py tests\\unit\\test_task_runtime_service.py tests\\integration\\test_preview_approval_api.py tests\\contract\\test_preview_approval_contracts.py -q

Resultados:
- Kotlin compile: BUILD SUCCESSFUL.
- Android focused tests: BUILD SUCCESSFUL.
- Backend approval/runtime focused tests: 44 passed.

## Smoke real
Não executado nesta rodada via operador real com criação de arquivo. Pelo critério do sprint, não declaro APPROVAL_UX_READY pleno.

## Status final obrigatório
BACKEND_READY: sim
UX_OPERATOR_READY: parcial
SPEAKER_TRUTH_READY: sim

## Limitações
- A UX mobile usa extração de approval/task id do payload humanizado atual; o backend já fornece o metadata no pipeline, mas Chat depende do view-model atual carregar essa referência.
- Sem smoke real de arquivo criado, o veredito permanece com warnings.
- Config Governance API e Workspace Permission Matrix seguem fora de escopo.
