from __future__ import annotations

from pathlib import Path

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore


def _service(tmp_path: Path) -> AgentSessionKernelService:
    return AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))


def _run(service: AgentSessionKernelService, agent_id: str = "aipinho"):
    session = service.create_session(agent_id, AgentSessionCreateRequest(title="Timeline"))
    run = service.create_run(agent_id, session.session_id, AgentRunCreateRequest(operation_type="analysis", status="running"))
    return session, run


def test_append_event_has_monotonic_run_and_session_sequence(tmp_path):
    service = _service(tmp_path)
    session, first_run = _run(service)
    second_run = service.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="validation", status="running"))

    e1 = service.add_event(first_run.run_id, AgentEventCreateRequest(event_type="agent_run_started", human_message="Started"))
    e2 = service.add_event(first_run.run_id, AgentEventCreateRequest(event_type="agent_explanation", human_message="Working"))
    e3 = service.add_event(second_run.run_id, AgentEventCreateRequest(event_type="validation_started", human_message="Validating"))

    assert [e1.sequence, e2.sequence] == [2, 3]  # agent_run_created is hidden sequence 1
    assert e3.sequence == 2
    assert [e1.session_sequence, e2.session_sequence, e3.session_sequence] == [3, 4, 5]


def test_list_events_by_run_and_session_do_not_mix_agents(tmp_path):
    service = _service(tmp_path)
    aipinho_session, aipinho_run = _run(service, "aipinho")
    codex_session, codex_run = _run(service, "codex")

    service.add_event(aipinho_run.run_id, AgentEventCreateRequest(event_type="agent_explanation", human_message="Aipinho"))
    service.add_event(codex_run.run_id, AgentEventCreateRequest(event_type="agent_explanation", human_message="Codex"))

    aipinho_timeline = service.timeline_response("aipinho", aipinho_session.session_id)
    codex_timeline = service.timeline_response("codex", codex_session.session_id)

    assert all(event.agent_id == "aipinho" for event in aipinho_timeline.events)
    assert all(event.agent_id == "codex" for event in codex_timeline.events)


def test_after_event_id_and_after_sequence_are_incremental(tmp_path):
    service = _service(tmp_path)
    session, run = _run(service)
    first = service.add_event(run.run_id, AgentEventCreateRequest(event_type="agent_explanation", human_message="First"))
    second = service.add_event(run.run_id, AgentEventCreateRequest(event_type="agent_next_action", human_message="Second"))
    third = service.add_event(run.run_id, AgentEventCreateRequest(event_type="validation_started", human_message="Third"))

    after_id = service.timeline_response("aipinho", session.session_id, after_event_id=first.event_id)
    after_seq = service.timeline_response("aipinho", session.session_id, after_sequence=second.session_sequence)
    missing = service.timeline_response("aipinho", session.session_id, after_event_id="missing_event")

    assert [event.event_id for event in after_id.events] == [second.event_id, third.event_id]
    assert [event.event_id for event in after_seq.events] == [third.event_id]
    assert missing.events == []


def test_visibility_normal_details_and_mapper_cards(tmp_path):
    service = _service(tmp_path)
    session, run = _run(service)
    visible = service.add_event(run.run_id, AgentEventCreateRequest(event_type="approval_required", human_message="Approve patch", approval_id="approval_x"))
    hidden = service.add_event(run.run_id, AgentEventCreateRequest(event_type="shell_stdout", human_message="Hidden output", visible_in_timeline=False))

    normal = service.timeline_response("aipinho", session.session_id, mode="normal")
    details = service.timeline_response("aipinho", session.session_id, mode="details")

    assert visible.event_id in {event.event_id for event in normal.events}
    assert hidden.event_id not in {event.event_id for event in normal.events}
    assert hidden.event_id in {event.event_id for event in details.events}
    approval_card = next(card for card in details.cards if card.event_id == visible.event_id)
    assert approval_card.title == "Aprovacao necessaria"
    assert approval_card.details["approval_id"] == "approval_x"


def test_state_aggregation_from_events_keeps_pending_and_validation_failed(tmp_path):
    service = _service(tmp_path)
    session, pending_run = _run(service, "codex")
    service.add_event(pending_run.run_id, AgentEventCreateRequest(event_type="approval_required", human_message="Need approval", approval_id="approval_1"))
    service.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="simple_chat", status="completed"))

    assert service.session_state("codex", session.session_id).latest_status == "pending_approval"

    validation_run = service.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="validation", status="completed"))
    service.add_event(validation_run.run_id, AgentEventCreateRequest(event_type="validation_failed", human_message="Tests failed"))

    assert service.session_state("codex", session.session_id).latest_status == "validation_failed"


def test_blocked_cancelled_and_polling_contract(tmp_path):
    service = _service(tmp_path)
    session, run = _run(service)

    active = service.timeline_response("aipinho", session.session_id)
    assert active.polling.enabled is True
    assert active.polling.recommended_interval_seconds == 5

    service.add_event(run.run_id, AgentEventCreateRequest(event_type="agent_run_blocked", human_message="Blocked", payload_sanitized={"reason_code": "policy"}))
    blocked = service.session_state("aipinho", session.session_id)
    assert blocked.latest_status == "blocked"
    assert blocked.blocked_reason_code == "policy"

    cancelled_run = service.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="cancel", status="cancelled"))
    assert service.run_events_response(cancelled_run.run_id).status == "cancelled"


def test_sanitization_and_raw_hidden_in_normal_timeline(tmp_path):
    service = _service(tmp_path)
    session, run = _run(service)
    event = service.add_event(
        run.run_id,
        AgentEventCreateRequest(
            event_type="agent_explanation",
            human_message="Authorization: Bearer SECRET_VALUE_12345",
            payload_sanitized={"token": "Bearer SECRET_VALUE_12345"},
            raw_ref="raw_secret_ref",
        ),
    )

    normal = service.timeline_response("aipinho", session.session_id, mode="normal")
    card = next(card for card in normal.cards if card.event_id == event.event_id)

    assert "[REDACTED_SECRET]" in card.body
    assert "SECRET_VALUE_12345" not in card.body
    assert "raw_ref" not in card.model_dump()
    assert card.raw_available is True
