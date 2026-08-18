from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_launcher_exposes_active_agent_surfaces_in_operational_order() -> None:
    source = _source("apps/launcher/ui/launcher_app.py")
    expected = (
        "Agent Marketplace",
        "Chat",
        "Gemini",
        "Codex",
        "Planning",
        "Pipeline",
        "Approvers",
    )
    positions = [
        re.search(rf'self\._add_tab\(\s*".*{name}"', source).start()
        for name in expected
    ]
    assert positions == sorted(positions)
    assert "LucioAgentTab" not in source
    assert "Lúcio" not in source
    assert "Lucio" not in source


def test_launcher_universal_approvers_tab_uses_canonical_endpoints() -> None:
    app_source = _source("apps/launcher/ui/launcher_app.py")
    tab_source = _source("apps/launcher/ui/tabs/universal_approvers_tab.py")
    client_source = _source("apps/launcher/ui/api/universal_approver_client.py")

    assert "UniversalApproverClient" in app_source
    assert "UniversalApproversTab" in app_source
    assert "/api/v1/universal-approvers" in client_source
    assert "/api/v1/universal-approvers/approval-timeline" in client_source
    assert "/api/v1/universal-approvers/approvals/{approval_id}/text-decision" in client_source
    assert "if gemini" not in tab_source.lower()
    assert "if codex" not in tab_source.lower()


def test_generic_agent_chat_is_scrollable_and_has_neon_session_actions() -> None:
    source = _source("apps/launcher/ui/tabs/agent_desktop_tab.py")
    for fragment in (
        "tk.Scrollbar(",
        '"Sessoes"',
        '"Abrir chat"',
        '"Renomear"',
        '"Deletar"',
        '"Copiar conversa"',
        '"Exportar"',
        '"Expandir"',
        '"Buscar na conversa"',
        '"Nova mensagem"',
        '"Delegation Timeline"',
        '"Resposta direta do Provider\\nSem delegacao"',
        "Delegation ID:",
        "_delegation_from_payload",
        "Universal Task Session / 5s",
        "_at_bottom",
        "Path(__file__).resolve()",
        "_rename_dialog",
        "_confirm_dialog",
        "COLORS[\"cyan\"]",
        "COLORS[\"pink\"]",
    ):
        assert fragment in source
    assert "simpledialog" not in source


def test_launcher_pipeline_renders_execution_graph_and_node_actions() -> None:
    source = _source("apps/launcher/ui/tabs/pipeline_tab.py")
    client = _source("apps/launcher/ui/api/pipeline_client.py")

    for fragment in (
        '"Execution Graph"',
        "_render_execution_graph",
        "_execution_graph_from_payload",
        '"Retry Node"',
        '"Cancel Node"',
        "retry_node",
        "cancel_node",
        "/execution-graph/nodes/",
        "/retry",
        "/cancel",
    ):
        assert fragment in source or fragment in client


def test_launcher_planning_tab_uses_mobile_view_model_and_universal_planning_endpoints() -> None:
    app_source = _source("apps/launcher/ui/launcher_app.py")
    tab_source = _source("apps/launcher/ui/tabs/planning_tab.py")
    client = _source("apps/launcher/ui/api/pipeline_client.py")

    assert "PlanningTab" in app_source
    assert '"Planning"' in app_source
    for fragment in (
        '"Planning"',
        "mobile_pipeline()",
        "_planning_report_from_payload",
        "planning_report",
        "parallel_groups",
        "risk_level",
    ):
        assert fragment in tab_source
    assert "/planning/report" in client
    assert "/planning/nodes/" in client
    assert "/replan" in client


def test_launcher_agent_marketplace_tab_uses_canonical_marketplace_endpoints() -> None:
    app_source = _source("apps/launcher/ui/launcher_app.py")
    tab_source = _source("apps/launcher/ui/tabs/agent_marketplace_tab.py")
    client_source = _source("apps/launcher/ui/api/agent_marketplace_client.py")

    assert "AgentMarketplaceClient" in app_source
    assert "AgentMarketplaceTab" in app_source
    assert '"Agent Marketplace"' in app_source
    assert "/api/v1/agent-marketplace/snapshot" in client_source
    assert "/api/v1/agent-marketplace/capabilities/" in client_source
    assert "/api/v1/agent-marketplace/agents/{agent_id}/heartbeat" in client_source
    assert "Capability Marketplace" in tab_source
    assert "if gemini" not in tab_source.lower()
    assert "if codex" not in tab_source.lower()


def test_aipinho_chat_is_scrollable_and_uses_themed_session_dialogs() -> None:
    source = _source("apps/launcher/ui/tabs/chat_tab.py")
    assert "tk.Scrollbar(" in source
    assert "_show_neon_text_dialog" in source
    assert "_show_neon_confirm_dialog" in source
    assert "simpledialog" not in source
    assert "askyesno" not in source
    assert "selected_session_id" in source
    assert "_remember_session" in source


def test_agent_ui_sources_do_not_contain_frontend_secrets() -> None:
    sources = "\n".join(
        _source(path)
        for path in (
            "apps/launcher/ui/agent_catalog.py",
            "apps/launcher/ui/api/agent_api_client.py",
            "apps/launcher/ui/tabs/agent_desktop_tab.py",
            "apps/launcher/ui/launcher_app.py",
        )
    )
    assert "OPENAI_API_KEY" not in sources
    assert "GEMINI_API_KEY" not in sources
    assert "AIza" not in sources
    assert "sk-proj-" not in sources
