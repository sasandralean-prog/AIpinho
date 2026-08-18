# Sprint 21 - Route Matrix

Gerado em: 2026-06-25 07:50:40

## Matriz
{
  "generated_at": "2026-06-25 07:50:40",
  "route_families": [
    {
      "family": "chat",
      "routes": [
        "POST /api/v1/chat",
        "POST /api/v1/chat/preview",
        "POST /api/v1/chat/approval-command",
        "GET /api/v1/chat/status",
        "GET /api/v1/chat/diagnostics"
      ],
      "status": "official",
      "notes": "Chat-native governance path; approval-command is required for text approvals."
    },
    {
      "family": "chat sessions",
      "routes": [
        "POST /api/v1/chat/sessions",
        "GET /api/v1/chat/sessions/{session_id}/messages",
        "POST /api/v1/chat/sessions/{session_id}/messages"
      ],
      "status": "official",
      "notes": "GET /api/v1/sessions is not the canonical chat session list route."
    },
    {
      "family": "continue openai-compatible",
      "routes": [
        "GET /v1/models",
        "POST /v1/chat/completions",
        "POST /v1/integrations/vscode/actions/preview",
        "POST /v1/integrations/vscode/actions/execute"
      ],
      "status": "official_adapter",
      "notes": "Must remain assistant/programming compatible and not bypass governance for side effects."
    },
    {
      "family": "approvals",
      "routes": [
        "GET /api/v1/approvals/pending",
        "POST /api/v1/approvals",
        "POST /api/v1/approvals/{approval_id}/decide"
      ],
      "status": "official",
      "notes": "Queue pollution from old approvals remains a lifecycle backlog."
    },
    {
      "family": "previews",
      "routes": [
        "POST /api/v1/previews",
        "GET /api/v1/previews/{preview_id}"
      ],
      "status": "official",
      "notes": "Used by write and shell approval previews."
    },
    {
      "family": "config governance",
      "routes": [
        "GET /api/v1/config/status",
        "GET /api/v1/config/permission-matrix",
        "GET/POST config governance endpoints"
      ],
      "status": "official",
      "notes": "Config endpoints are the source for permission matrix inspection."
    },
    {
      "family": "runtime queue health",
      "routes": [
        "GET /api/v1/runtime/queue-health"
      ],
      "status": "missing",
      "notes": "Probe returned 404; keep as backlog, do not duplicate route blindly."
    },
    {
      "family": "legacy session status",
      "routes": [
        "GET /api/v1/session/status"
      ],
      "status": "missing_or_legacy",
      "notes": "Probe returned 404; canonical session/status map should be clarified."
    }
  ],
  "evidence_files": [
    "route_rg.txt",
    "governance_rg.txt"
  ]
}
