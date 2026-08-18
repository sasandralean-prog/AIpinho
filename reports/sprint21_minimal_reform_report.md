# Sprint 21 - Minimal Reform Report

Gerado em: 2026-06-25 07:50:40

## Reforma minima
{
  "generated_at": "2026-06-25 07:50:40",
  "files_changed": [
    "config/chat/canonical_operation_map.yaml",
    "config/chat/chat_operation_routing_policy.yaml",
    "src/aipinho/services/chat/chat_operation_router_service.py",
    "src/aipinho/services/chat/chat_service.py",
    "src/aipinho/api/routers/chat_router.py",
    "tests/unit/test_chat_operation_router_service.py",
    "tests/unit/test_governed_approval_continuation.py",
    "tests/integration/test_chat_api.py"
  ],
  "root_causes": [
    "Shell intent had no high-priority governed shell route before build/project generation terms.",
    "GovernedWriteChatService could indicate approval requirement without materializing an approval record.",
    "Chat router propagated invalid session id as unhandled ValueError."
  ],
  "why_generic": [
    "Routing is policy/config term based, not specific prompt/path based.",
    "Approval materialization applies to any governed file write pending approval without approval_id.",
    "Session error handling applies to any invalid session id."
  ],
  "tests": [
    "python -m py_compile src\\aipinho\\services\\chat\\chat_service.py src\\aipinho\\services\\chat\\chat_operation_router_service.py src\\aipinho\\api\\routers\\chat_router.py -> passed",
    "python -m pytest tests\\unit\\test_chat_operation_router_service.py tests\\unit\\test_governed_approval_continuation.py tests\\integration\\test_chat_api.py -q -> 77 passed in 83.33s",
    "In-process TestClient firetests for chat governance -> evidence in reports/sprint21_evidence/firetests_current_code"
  ],
  "firetest_summary": [
    {
      "case": "conversation_oi",
      "http_status": 200,
      "status": "degraded",
      "operation_type": "conversation",
      "message_type": "assistant_final_answer",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": [],
      "safe_to_execute": false,
      "warnings": [],
      "text_sample": "Nao consegui gerar uma resposta conversacional pelo modelo leve agora. O Intent Map classificou como conversa simples e o Model Gate tentou a role speaker, mas o runtime/modelo foi bloqueado ou ficou indisponivel: timeout, stderr_captured."
    },
    {
      "case": "reasoning_math",
      "http_status": 200,
      "status": "ok",
      "operation_type": "conversation",
      "message_type": "assistant_final_answer",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": [],
      "safe_to_execute": false,
      "warnings": [],
      "text_sample": "4."
    },
    {
      "case": "permission_status",
      "http_status": 200,
      "status": "ok",
      "operation_type": "permission_status",
      "message_type": "assistant_final_answer",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": [],
      "safe_to_execute": null,
      "warnings": [],
      "text_sample": "Permissoes atuais da AIpinho:\n\nLeitura permitida:\n- C:\\Dev\\AIpinho (system_mutable; read; approval obrigatorio)\n- C:\\Users\\[REDACTED]\\Documents\\AIpinhoTestes (target_mutable; read; approval obrigatorio)\n- C:\\Dev\\AI\\coding-brain-supervisor ("
    },
    {
      "case": "read_only_explicit",
      "http_status": 200,
      "status": "ok",
      "operation_type": "workspace_metadata_query",
      "message_type": "assistant_final_answer",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": [],
      "safe_to_execute": null,
      "warnings": [],
      "text_sample": "Consulta read-only concluida. Nao criei arquivo e nao gerei relatorio.\n\nWorkspace: C:\\Users\\[REDACTED]\\Documents\\AIpinhoTestes\\Sprint-File-Sync-main\n\nArquivos perguntados:\n- build.gradle: nao\n- package.json: sim\n\nArquivos de entrada aparent"
    },
    {
      "case": "negative_constraints",
      "http_status": 200,
      "status": "needs_clarification",
      "operation_type": "readonly_project_analysis",
      "message_type": "clarification_request",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": [],
      "safe_to_execute": null,
      "warnings": [
        "workspace_required_but_missing"
      ],
      "text_sample": "Preciso saber qual workspace ou projeto devo analisar em modo somente leitura. Escolha um workspace legivel ou informe um caminho registrado."
    },
    {
      "case": "write_request_preview",
      "http_status": 200,
      "status": "pending_approval",
      "operation_type": "governed_file_write",
      "message_type": "task_status_update",
      "task_id": null,
      "approval_id": "approval_054242937bb0422fb7189b4576ca8f0c",
      "preview_id": "preview_010e2b23d3d74ae884d1366806923eef",
      "approval_required": null,
      "approval_required_for": [
        "write_files"
      ],
      "safe_to_execute": false,
      "warnings": [
        "approval_required_before_workspace_write"
      ],
      "text_sample": "A escrita foi identificada, mas a policy exige aprovacao antes de qualquer gravacao. Nenhum arquivo foi escrito nesta etapa."
    },
    {
      "case": "shell_request_preview",
      "http_status": 200,
      "status": "pending_approval",
      "operation_type": "governed_shell_request",
      "message_type": "task_status_update",
      "task_id": null,
      "approval_id": "approval_279f7c257596497aaafb37ded7291f08",
      "preview_id": "preview_1bd233c529ee4ccabc0864b2dc0b8ce9",
      "approval_required": null,
      "approval_required_for": [
        "run_command"
      ],
      "safe_to_execute": false,
      "warnings": [
        "shell_requires_approval",
        "no_shell_executed"
      ],
      "text_sample": "O comando foi reconhecido como shell governado e precisa de aprovacao antes de qualquer execucao. Nada foi executado. Revise o approval no Pipeline ou responda no chat com o approval_id."
    },
    {
      "case": "permission_grant_natural",
      "http_status": 200,
      "status": "ok",
      "operation_type": "conversation",
      "message_type": "assistant_final_answer",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": [],
      "safe_to_execute": false,
      "warnings": [],
      "text_sample": "A autorização para escrita em C:\\Users\\afae\\Documents\\AIpinhoTestes para esta sessão foi concedida."
    },
    {
      "case": "approval_textual_fake",
      "http_status": 200,
      "status": "blocked",
      "operation_type": "approval_command",
      "message_type": "blocked_policy_message",
      "task_id": null,
      "approval_id": null,
      "preview_id": null,
      "approval_required": null,
      "approval_required_for": null,
      "safe_to_execute": null,
      "warnings": [
        "approval_not_found"
      ],
      "text_sample": "Nao consegui executar esse comando de approval. Motivo: approval_not_found. Use um approval_id pendente ou um task_id com approvals seguros."
    }
  ]
}
