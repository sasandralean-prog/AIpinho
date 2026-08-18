# Approval x Task Queue UX Diagnosis

Created: 20260623_202203

## Verdict

`approval_task_queue_ux_incongruence_confirmed_structural`

## Runtime Snapshot

- **health**: `ok on http://127.0.0.1:9088/api/v1/health during diagnosis`
- **task_runtime_queue**: `{'total_visible': 0, 'requires_decision': 0, 'status': 'ok'}`
- **approvals_pending_after_reconcile**: `0`
- **approval_store_counts_after_reconcile**: `{'approved': 703, 'expired': 81, 'cancelled': 3, 'pending': 0}`
- **live_reproduction**: `No live pending approval/task existed after lazy expiration reconciliation; diagnosis is structural and trace-based.`

## Findings

### F1 - Launcher Pipeline e Mobile Pipeline usam fontes de verdade diferentes
- Severity: `high`
- Risk: Launcher pode mostrar cards vazios/obsoletos enquanto o mobile mostra a fila runtime real, ou o inverso.
- Evidence:
  - apps/launcher/ui/api/pipeline_client.py usa /api/v1/tasks/cards e /api/v1/approvals/pending.
  - src/aipinho/api/routers/task_sync_router.py serve /api/v1/tasks/cards via TaskSyncService.
  - src/aipinho/services/interaction/interaction_core.py: TaskSyncService.list_cards reconstr?i cards apenas de eventos task_card_created.
  - apps/mobile/android/.../PipelineScreen.kt usa /api/v1/mobile/view-model/pipeline.
  - src/aipinho/services/mobile_view_models/pipeline_mobile_aggregator.py usa TaskRuntimeService.queue_status().snapshot.
- Recommended fix: Manter /api/v1/tasks/cards por compatibilidade, mas faz?-lo derivar de TaskRuntimeService/TaskQueueService ou trocar o Launcher para o view-model/endpoint unificado.

### F2 - Approval Center mistura approvals vinculados a TaskRun e approvals standalone
- Severity: `high`
- Risk: UX pode exibir aprova??o acion?vel sem task selecionada; usu?rio v? fila vazia mas approval pendente, ou aprova algo que n?o retoma TaskRun.
- Evidence:
  - ApprovalRequest possui run_id/task_id opcionais.
  - TaskQueueService s? reconcilia approvals quando run.approval_id est? preenchido.
  - WorkspaceFlowService, ConfigGovernanceService, ArtifactApprovalBridge, PatchApplyApprovalBridge, MemoryApprovalBridge, Tools e Codex Agent criam ApprovalRequest que podem n?o ter run_id/task_id.
  - Launcher Pipeline renderiza todos os /api/v1/approvals/pending no Approval Center.
- Recommended fix: Criar/fortalecer uma fila unificada de approvals com campos owner_type, linked_task_run_id, continuation_mode e safe_actions por dom?nio.

### F3 - Mobile escolhe approval por varredura de metadata, n?o por sele??o expl?cita
- Severity: `medium`
- Risk: Quando novos cards t?cnicos tamb?m carregarem approval_id, o bot?o Aprovar/Negar pode atuar sobre o approval errado.
- Evidence:
  - PipelineScreen.kt usa latestMetadataValue(lastPipelinePayload, 'approval_id').
  - O m?todo percorre cards de tr?s para frente e pega o primeiro metadata.approval_id v?lido.
  - PipelineMobileAggregator atualmente coloca approval_id dentro do card pipeline_approval, mas n?o h? campo top-level selected_approval.
- Recommended fix: Expor selected_approval no MobilePipelineViewModel e fazer a UX acionar esse objeto expl?cito, n?o metadata gen?rico.

### F4 - Fila de tasks ignora approvals standalone por desenho, mas a UX n?o explica essa distin??o
- Severity: `medium`
- Risk: Contador 'precisam de permiss?o' pode ser 0 enquanto /approvals/pending tem itens standalone.
- Evidence:
  - PipelineMobileAggregator._pending_approval(run) s? olha run.approval_id.
  - TaskQueueSnapshot.requires_decision_count conta run com approval pending ou waiting_input sem approval.
  - /api/v1/approvals/pending lista approvals globais.
- Recommended fix: Separar contadores: tasks_requires_decision e standalone_approvals_pending; rotular cada tipo no cockpit.

### F5 - Expira??o de approvals ? lazy e pode causar aparente diverg?ncia transit?ria
- Severity: `medium`
- Risk: UX/relat?rios que leem arquivos diretamente ou endpoints diferentes podem divergir at? o pr?ximo acesso ao ApprovalService.
- Evidence:
  - ApprovalService.list_approvals chama _reconcile_expiration.
  - Snapshot em disco antes do endpoint mostrou 3 pending; chamada a /api/v1/approvals/pending reconciliou e depois o disco mostrou 0 pending e 81 expired.
- Recommended fix: Centralizar toda leitura de approvals no ApprovalService e retornar metadata de reconciliacao nos endpoints de lista.

### F6 - TaskSyncService baseado em eventos n?o carrega approval_id de TaskRun runtime
- Severity: `medium`
- Risk: Launcher pode renderizar task sem bot?es de approval mesmo quando a TaskRun tem approval_id.
- Evidence:
  - TaskSyncService.list_cards s? l? eventos task_card_created e monta TaskCard sem buscar TaskRunStore.
  - PipelinePresentationMapper tenta approval_id direto no card, mas TaskCard padr?o n?o cont?m esse campo.
- Recommended fix: Task cards devem incluir approval_id/status a partir de TaskRuntimeService ou deixar de ser usados como fonte operacional.

## Recommended Patch Plan

- Introduzir ApprovalQueueViewService ou ApprovalWorkItemService que normalize approvals de TaskRun e standalone.
- Adicionar campos no view-model: selected_task_id, selected_approval_id, selected_approval_kind, selected_continuation_mode, task_queue_count, standalone_approval_count.
- Trocar Launcher Pipeline para endpoint unificado ou refatorar /api/v1/tasks/cards para usar TaskRuntimeService/TaskQueueService mantendo compat.
- No mobile, substituir latestMetadataValue por leitura de selected_approval_id top-level.
- Desabilitar/rotular safe batch quando approval n?o pertence a TaskRun.
- Adicionar testes de regress?o para approval linked vs standalone e diverg?ncia Launcher/Mobile.

## Notes

No code was changed in this diagnostic pass. No secrets were printed.
