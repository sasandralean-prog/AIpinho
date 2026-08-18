from __future__ import annotations

import json

from apps.launcher.ui.agent_catalog import agent_endpoint
from apps.launcher.ui.api.agent_api_client import DesktopAgentApiClient


def _transport(calls):
    def send(method, url, headers, body, timeout):
        calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "payload": json.loads(body.decode("utf-8")) if body else None,
                "timeout": timeout,
            }
        )
        return 200, {"status": "ok", "sessions": [], "messages": []}

    return send


def test_agent_catalog_exposes_separate_governed_namespaces() -> None:
    assert agent_endpoint("codex_agent").route_prefix == "/api/v1/codex-agent"
    assert agent_endpoint("gemini_executor").route_prefix == "/api/v1/gemini-executor"


def test_lucio_is_not_exposed_in_active_launcher_catalog() -> None:
    try:
        agent_endpoint("lucio")
    except KeyError:
        return
    raise AssertionError("disabled Lucio must not be exposed as an active launcher agent")


def test_codex_rename_uses_patch_and_workspace_context() -> None:
    calls = []
    client = DesktopAgentApiClient(
        "http://127.0.0.1:9088",
        agent_endpoint("codex_agent"),
        token="test-token",
        transport=_transport(calls),
    )

    client.rename_session("session one", "Novo titulo")
    client.send("session one", "Analise o contexto", "workspace-id")

    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/api/v1/codex-agent/sessions/session%20one/rename")
    assert calls[1]["payload"]["workspace_context"] == "workspace-id"
    assert "workspace_id" not in calls[1]["payload"]
    assert calls[1]["headers"]["Authorization"] == "Bearer test-token"


def test_codex_and_gemini_keep_provider_specific_payloads() -> None:
    for agent_id, workspace_key in (
        ("codex_agent", "workspace_context"),
        ("gemini_executor", "workspace_context"),
    ):
        calls = []
        client = DesktopAgentApiClient(
            "http://localhost:9088",
            agent_endpoint(agent_id),
            transport=_transport(calls),
        )

        client.send("session", "mensagem", "workspace")

        assert calls[0]["payload"][workspace_key] == "workspace"
        assert "workspace_id" not in calls[0]["payload"]
        assert calls[0]["payload"]["operation_type"] == agent_endpoint(agent_id).operation_type


def test_view_model_and_session_lifecycle_use_canonical_agent_routes() -> None:
    calls = []
    client = DesktopAgentApiClient(
        "http://localhost:9088",
        agent_endpoint("codex_agent"),
        transport=_transport(calls),
    )

    client.create_session("Sessao")
    client.messages("session")
    client.view_model("session", after_event_id="event")
    client.delete_session("session")

    assert [call["method"] for call in calls] == ["POST", "GET", "GET", "DELETE"]
    assert calls[2]["url"].endswith(
        "/api/v1/codex-agent/sessions/session/view-model?after_event_id=event"
    )
