from __future__ import annotations

import pytest

from aipinho.schemas.multi_agent_observability import DebuggerEventView, ObservabilityCard


@pytest.mark.multi_agent
@pytest.mark.ui_contract
def test_mobile_launcher_cards_keep_raw_hidden_and_copy_sanitized():
    card = ObservabilityCard(
        card_id="artifact_card",
        title="Artifact",
        status="ready",
        severity="info",
        summary="Artifact pronto para download autenticado.",
        details={"transport": "Authorization header", "url_policy": "no_token_in_url"},
        evidence_refs=["artifact:agent_artifact_test"],
    )

    payload = card.model_dump()

    assert "raw_default_visible" not in payload
    assert payload["details"]["url_policy"] == "no_token_in_url"
    assert "token=" not in str(payload).lower()


@pytest.mark.multi_agent
@pytest.mark.ui_contract
def test_debugger_event_view_redacts_secret_like_payloads():
    event = DebuggerEventView(
        event_id="event_1",
        run_id="run_1",
        session_id="session_1",
        agent_id="aipinho",
        event_type="provider_status",
        status="received",
        severity="info",
        human_message="Provider configurado.",
        payload_sanitized={"api_key": "[REDACTED_SECRET]"},
        evidence_refs=[],
    )

    text = str(event.model_dump())
    assert "AIza" not in text
    assert "sk-" not in text
    assert "[REDACTED_SECRET]" in text
