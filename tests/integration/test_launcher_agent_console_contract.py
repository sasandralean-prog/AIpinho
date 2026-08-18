from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_launcher_registers_agent_console_tab_and_client() -> None:
    launcher_source = (ROOT / "apps" / "launcher" / "ui" / "launcher_app.py").read_text(encoding="utf-8")

    assert "AgentConsoleClient" in launcher_source
    assert "AgentConsoleTab" in launcher_source
    assert '"agent_console"' in launcher_source
    assert '"Agentes"' in launcher_source


def test_agent_console_client_uses_canonical_backend_endpoints() -> None:
    client_source = (ROOT / "apps" / "launcher" / "ui" / "api" / "agent_console_client.py").read_text(encoding="utf-8")

    expected_endpoints = [
        "/api/v1/agent-bridge/status",
        "/api/v1/agent-bridge/active",
        "/api/v1/agent-bridge/tasks/",
        "/api/v1/artifacts",
        "/api/v1/approvals/pending",
        "/api/v1/locks",
        "/api/v1/debugger/recent",
        "/api/v1/debugger/by-bridge-task/",
        "/api/v1/debugger/traces/",
    ]
    for endpoint in expected_endpoints:
        assert endpoint in client_source


def test_agent_console_tab_exposes_bridge_artifact_trace_approval_and_lock_sections() -> None:
    tab_source = (ROOT / "apps" / "launcher" / "ui" / "tabs" / "agent_console_tab.py").read_text(encoding="utf-8")

    expected_labels = [
        "Agent Console",
        "Bridge Monitor",
        "Artifact Center",
        "Trace Center",
        "Approval Center",
        "Workspace Locks",
        "Baixar",
        "Abrir pasta",
        "Revalidar",
        "Provenance",
        "Bridge trace",
        "Exportar",
        "Copiar trace",
        "Aprovar",
        "Negar",
        "Preview",
        "Cancelar task",
        "Liberar",
        "Override",
        "Status leve",
    ]
    for label in expected_labels:
        assert label in tab_source
