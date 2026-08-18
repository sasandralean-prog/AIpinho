from __future__ import annotations

import pytest

from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.events.event_core import (
    EventContractRegistryService,
    EventContractValidator,
    EventPublisherService,
    EventStoreRepository,
    contains_secret,
)
from aipinho.services.interaction.interaction_core import SpeakerTruthService


def test_event_registry_loads_contracts() -> None:
    status = EventContractRegistryService().status()
    assert status["status"] == "ok"
    assert status["contracts_loaded"] >= 10
    assert status["unknown_event_default"] == "blocked"


def test_unknown_event_is_blocked() -> None:
    request = EventPublishRequest(event_type="not_registered", source_service="chat", human_summary="Evento nao registrado.")
    result = EventContractValidator().validate(request)
    assert result.allowed is False
    assert "unknown_event_type" in result.reasons


def test_event_without_human_summary_is_blocked() -> None:
    request = EventPublishRequest(event_type="message_received", source_service="chat", human_summary="")
    result = EventContractValidator().validate(request)
    assert result.allowed is False
    assert "missing_human_summary" in result.reasons


def test_event_secret_payload_is_blocked() -> None:
    request = EventPublishRequest(
        event_type="message_received",
        source_service="chat",
        human_summary="Mensagem recebida.",
        payload={"authorization": "Bearer abcdef123456"},
    )
    result = EventContractValidator().validate(request)
    assert result.allowed is False
    assert "secret_detected_in_public_event" in result.reasons


def test_secret_detection_does_not_treat_contract_token_vocabulary_as_credential() -> None:
    assert contains_secret({"path_token_groups": [["patch", "plan"]]}) is False
    assert contains_secret({"required_content_token_groups": {"risk": ["risk"]}}) is False
    assert contains_secret({"access_token": "abc"}) is True
    assert contains_secret({"notes": "Bearer abcdef123456"}) is True


def test_speaker_uses_source_event_and_blocks_false_progress() -> None:
    event = EventPublisherService().publish(EventPublishRequest(
        event_type="plan_created",
        source_service="planner",
        human_summary="Plano criado para revisao.",
        payload={"task_id": "task_sprint33_unit"},
    ))
    result = SpeakerTruthService().from_event(event.event_id)
    assert result.allowed is True
    assert "Ainda nao apliquei" in result.message

    blocked = SpeakerTruthService().from_event(event.event_id, "Corrigi e apliquei o patch.")
    assert blocked.allowed is False
    assert "completion_claim_without_event" in blocked.reasons


def test_publisher_rejects_unknown_event() -> None:
    with pytest.raises(ValueError):
        EventPublisherService().publish(EventPublishRequest(event_type="unknown_runtime_event", source_service="chat", human_summary="Nao registrar."))
