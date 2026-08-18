# Sprint 21 - Capability Matrix

Gerado em: 2026-06-25 07:50:40

## Matriz
{
  "generated_at": "2026-06-25 07:50:40",
  "summary": {
    "chat_model_status_available": false,
    "config_status_ok": false,
    "permission_matrix_available": false
  },
  "capabilities": [
    {
      "capability": "conversation",
      "status": "degraded_warning",
      "evidence": "conversation_oi degraded due provider timeout; reasoning_math returned 4."
    },
    {
      "capability": "permission_status",
      "status": "passed",
      "evidence": "firetest permission_status status=ok operation_type=permission_status."
    },
    {
      "capability": "readonly_workspace_metadata",
      "status": "passed",
      "evidence": "read_only_explicit status=ok, no task, no approval, no report generation."
    },
    {
      "capability": "governed_file_write_preview",
      "status": "passed",
      "evidence": "write_request_preview pending_approval with approval_id and preview_id; safe_to_execute=false."
    },
    {
      "capability": "governed_shell_preview",
      "status": "passed",
      "evidence": "shell_request_preview pending_approval with approval_id and preview_id; no_shell_executed warning."
    },
    {
      "capability": "approval_text_command",
      "status": "passed",
      "evidence": "approval_textual_fake returns blocked approval_not_found instead of conversation fallback."
    },
    {
      "capability": "workspace_write_alias",
      "status": "passed_by_tests",
      "evidence": "Focused test suite covers write_files approval path."
    },
    {
      "capability": "real_provider_runtime",
      "status": "warning",
      "evidence": "Simple greeting degraded due timeout/stderr; not fixed in Sprint 21."
    },
    {
      "capability": "vision_ocr_embedding_reranker",
      "status": "unverified",
      "evidence": "Not in Sprint 21 scope; no live provider validation claimed."
    }
  ],
  "permission_roles_snapshot": {}
}
