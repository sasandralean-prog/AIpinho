# Sprint 21 - Governance Audit

Gerado em: 2026-06-25 07:50:40

## Veredito
SPRINT21_GOVERNANCE_AUDIT_READY_WITH_WARNINGS

## Resumo
O Sprint 21 encontrou bugs reais no roteamento de shell, materializacao de approvals de escrita e erro de sessao invalida. Foram aplicados patches minimos e genericos. O backend vivo ainda precisa restart com permissao/admin para carregar a fonte corrigida.

## Achados
[
  {
    "id": "S21-F01",
    "severity": "P1",
    "title": "Shell requests from chat were routed as project/build flow instead of governed shell approval.",
    "evidence": "Live firetest before patch returned operation_type=project_generation for an npm test request.",
    "fix": "Added configurable governed_shell_request route and alias, with approval preview and no execution.",
    "status": "fixed_in_source"
  },
  {
    "id": "S21-F02",
    "severity": "P1",
    "title": "Governed write chat response could report pending_approval without an ApprovalRequest id.",
    "evidence": "Initial firetest returned pending_approval with approval_id=null.",
    "fix": "ChatService now wraps governed_file_write pending approval into TaskContractDraft, preview, and ApprovalRequest.",
    "status": "fixed_in_source"
  },
  {
    "id": "S21-F03",
    "severity": "P1",
    "title": "Invalid chat session id raised 500 instead of structured response.",
    "evidence": "Live backend returned ValueError invalid_session_id as 500 during audit probes.",
    "fix": "chat_router maps invalid_session_id to HTTP 409 structured error.",
    "status": "fixed_in_source"
  },
  {
    "id": "S21-F04",
    "severity": "P2",
    "title": "Pending approvals queue contains historical Continue/test approvals not linked to active run/task.",
    "evidence": "Preflight approvals evidence found 0 pending approvals in current endpoint snapshot.",
    "fix": "No destructive cleanup in Sprint 21; documented for lifecycle/reaper hygiene.",
    "status": "backlog"
  },
  {
    "id": "S21-F05",
    "severity": "P2",
    "title": "Some status endpoints expected by governance audit are absent or legacy-mismatched.",
    "evidence": "/api/v1/session/status -> 404; GET /api/v1/sessions -> 405; /api/v1/runtime/queue-health -> 404.",
    "fix": "No route duplication in Sprint 21; documented for canonical status map.",
    "status": "backlog"
  },
  {
    "id": "S21-F06",
    "severity": "P2",
    "title": "Live backend process still needs restart to load source fixes.",
    "evidence": "Port 9088 was held by PID 55752 and Stop-Process failed with access denied in previous run.",
    "fix": "Validated source with TestClient/pytest; operator/admin restart still required for live parity.",
    "status": "operational_warning"
  },
  {
    "id": "S21-F07",
    "severity": "P2",
    "title": "Conversational model path may degrade on simple greeting due provider timeout.",
    "evidence": "Current-code firetest conversation_oi status=degraded with timeout/stderr_captured; arithmetic deterministic path passed.",
    "fix": "Not changed in governance sprint; classify as provider/model runtime warning, not policy bypass.",
    "status": "backlog"
  }
]

## Arquivos tocados
[
  "config/chat/canonical_operation_map.yaml",
  "config/chat/chat_operation_routing_policy.yaml",
  "src/aipinho/services/chat/chat_operation_router_service.py",
  "src/aipinho/services/chat/chat_service.py",
  "src/aipinho/api/routers/chat_router.py",
  "tests/unit/test_chat_operation_router_service.py",
  "tests/unit/test_governed_approval_continuation.py",
  "tests/integration/test_chat_api.py"
]

## Testes
[
  "python -m py_compile src\\aipinho\\services\\chat\\chat_service.py src\\aipinho\\services\\chat\\chat_operation_router_service.py src\\aipinho\\api\\routers\\chat_router.py -> passed",
  "python -m pytest tests\\unit\\test_chat_operation_router_service.py tests\\unit\\test_governed_approval_continuation.py tests\\integration\\test_chat_api.py -q -> 77 passed in 83.33s",
  "In-process TestClient firetests for chat governance -> evidence in reports/sprint21_evidence/firetests_current_code"
]

## Avisos
[
  "Provider/model runtime ainda pode degradar conversa simples.",
  "Fila de approvals historicos precisa higiene em sprint proprio.",
  "Alguns endpoints de status esperados nao existem como rota canonica."
]
