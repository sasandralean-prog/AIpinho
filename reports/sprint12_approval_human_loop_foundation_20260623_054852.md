# Sprint 12 — Approval Human Loop Foundation

Timestamp: 20260623_054852
Projeto: AIpinho
Root: C:\Dev\AIpinho

## Veredito
GOVERNED_APPROVAL_FOUNDATION_READY_WITH_WARNINGS

## O que foi implementado/consolidado
- ApprovalRequest real com runtime/task/workspace/operation metadata.
- ApprovalDecision com escopo de decisão.
- Runtime coloca task em waiting_input quando approval é possível.
- Approval aprovado libera task para retomada governada.
- Approval negado cancela a TaskRun sem executar side effects pendentes.
- Endpoints approve/deny por approval e approve/deny safe batch por task.
- Parser textual explícito para APROVAR <approval_id>, NEGAR <approval_id>, APROVAR TODAS <task_id> e NEGAR TODAS <task_id>.
- Frases vagas continuam não liberando acesso irrestrito.
- Eventos novos: pproval_preview_created, pproval_batch_approved, pproval_batch_denied, 	ask_cancelled_after_denial, policy_blocked_no_approval_possible.

## Arquivos alterados
- src/aipinho/schemas/approvals/approval_event.py
- src/aipinho/services/approvals/approval_service.py
- src/aipinho/services/approvals/approval_task_continuation_service.py
- src/aipinho/services/runtime/task_queue_service.py
- src/aipinho/services/runtime/task_runtime_service.py
- src/aipinho/api/routers/task_runtime_router.py
- src/aipinho/services/chat/chat_approval_command_service.py
- config/runtime/task_run_event_policy.yaml
- tests/unit/test_governed_approval_continuation.py

## Endpoints relevantes
- GET /api/v1/approvals/pending
- GET /api/v1/approvals/{approval_id}
- POST /api/v1/approvals/{approval_id}/approve
- POST /api/v1/approvals/{approval_id}/deny
- GET /api/v1/tasks/{task_id}/approvals
- POST /api/v1/tasks/{task_id}/approvals/approve-safe-batch
- POST /api/v1/tasks/{task_id}/approvals/deny-safe-batch

## Testes executados
- python -m py_compile nos arquivos alterados.
- python -m pytest tests\\unit\\test_governed_approval_continuation.py -q
- python -m pytest tests\\unit\\test_governed_approval_continuation.py tests\\unit\\test_approval_preview_lifecycle.py tests\\unit\\test_approval_policy_service.py tests\\unit\\test_task_queue_service.py tests\\unit\\test_task_runtime_service.py tests\\integration\\test_preview_approval_api.py tests\\contract\\test_preview_approval_contracts.py -q

Resultado: 44 passed em bateria focada final.

## Warnings honestos
- O storage interno continua usando ejected; a UX/API expõe deny/denied por compatibilidade sem migração ampla.
- Não foi executado smoke real completo de criação de arquivo pelo operador neste relatório Sprint 12; isso fica coberto pelo Sprint 13/operador.
