from __future__ import annotations

from pathlib import Path

from aipinho.schemas.agents.contracts import (
    AgentEventCreateRequest,
    AgentMessageCreateRequest,
    AgentRunCreateRequest,
    AgentRunUpdateRequest,
    AgentSessionCreateRequest,
    AgentSessionUpdateRequest,
)
from aipinho.services.agents.agent_profile_registry_service import AgentProfileRegistryService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore


def _service(tmp_path: Path) -> AgentSessionKernelService:
    return AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))


def test_agent_profile_registry_lists_four_unique_agents():
    registry = AgentProfileRegistryService()
    profiles = registry.list_profiles()
    enabled = registry.list_profiles(enabled=True)

    assert {profile.agent_id for profile in profiles} == {"aipinho", "lucio", "codex", "gemini"}
    assert {profile.agent_id for profile in enabled} == {"aipinho", "codex", "gemini"}
    assert len({profile.agent_id for profile in profiles}) == len(profiles)
    assert all(profile.capabilities for profile in profiles)
    assert registry.status().profiles_loaded == 4


def test_agent_profile_registry_enabled_filter_with_temp_config(tmp_path):
    config = tmp_path / "agent_registry.yaml"
    config.write_text(
        """
agents:
  - agent_id: enabled_agent
    display_name: Enabled
    provider: local
    role: test
    enabled: true
  - agent_id: disabled_agent
    display_name: Disabled
    provider: local
    role: test
    enabled: false
""",
        encoding="utf-8",
    )

    registry = AgentProfileRegistryService(path=config, root=tmp_path)

    assert [profile.agent_id for profile in registry.list_profiles(enabled=True)] == ["enabled_agent"]
    assert [profile.agent_id for profile in registry.list_profiles(enabled=False)] == ["disabled_agent"]


def test_sessions_are_persistent_and_isolated_by_agent(tmp_path):
    service = _service(tmp_path)
    sessions = {
        agent_id: service.create_session(agent_id, AgentSessionCreateRequest(title=f"{agent_id} chat"))
        for agent_id in ["aipinho", "codex", "gemini"]
    }

    assert service.list_sessions("aipinho", include_compat=False)[0].session_id == sessions["aipinho"].session_id
    assert all(session.agent_id == "codex" for session in service.list_sessions("codex", include_compat=False))
    assert sessions["aipinho"].session_id not in {session.session_id for session in service.list_sessions("gemini", include_compat=False)}

    renamed = service.update_session("codex", sessions["codex"].session_id, AgentSessionUpdateRequest(title="Revisao"))
    assert renamed is not None
    assert renamed.title == "Revisao"

    deleted = service.delete_session("gemini", sessions["gemini"].session_id)
    assert deleted is not None
    assert deleted.deleted is True
    assert service.list_sessions("gemini", include_compat=False) == []


def test_lucio_profile_disabled_blocks_new_kernel_sessions(tmp_path):
    service = _service(tmp_path)

    try:
        service.create_session("lucio", AgentSessionCreateRequest(title="Lucio"))
    except PermissionError as exc:
        assert str(exc) == "agent_profile_disabled"
    else:  # pragma: no cover
        raise AssertionError("lucio_session_creation_should_be_blocked")


def test_messages_are_sanitized_and_raw_hidden_in_normal_mode(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("aipinho", AgentSessionCreateRequest(title="Chat"))
    message = service.add_message(
        "aipinho",
        session.session_id,
        AgentMessageCreateRequest(
            role="user",
            content_sanitized="Token Bearer SECRET_VALUE_12345",
            raw_ref="raw_hidden_ref",
        ),
    )

    public = service.list_messages("aipinho", session.session_id)[0].model_dump()
    assert public["message_id"] == message.message_id
    assert "raw_ref" not in public
    assert public["raw_available"] is True
    assert "[REDACTED_SECRET]" in public["content_sanitized"]


def test_runs_and_state_precedence_keep_pending_approval_over_simple_chat(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("codex", AgentSessionCreateRequest(title="Codex"))
    pending = service.create_run(
        "codex",
        session.session_id,
        AgentRunCreateRequest(operation_type="patch_preview", status="pending_approval", capabilities_requested=["write_workspace"]),
    )
    service.create_run(
        "codex",
        session.session_id,
        AgentRunCreateRequest(operation_type="simple_chat", status="completed"),
    )

    state = service.session_state("codex", session.session_id)

    assert state.latest_run_id == pending.run_id
    assert state.latest_status == "pending_approval"
    assert state.pending_approval == {"run_id": pending.run_id}


def test_validation_failed_and_blocked_have_precedence(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("aipinho", AgentSessionCreateRequest(title="Ops"))
    service.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="validation", status="completed"))
    failed = service.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="validation", status="validation_failed"))
    blocked = service.create_run("aipinho", session.session_id, AgentRunCreateRequest(operation_type="policy", status="blocked"))

    assert service.session_state("aipinho", session.session_id).latest_run_id == blocked.run_id
    assert service.update_run(failed.run_id, AgentRunUpdateRequest(status="failed")) is not None


def test_completed_run_is_not_overridden_by_resolved_tool_block(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("aipinho", AgentSessionCreateRequest(title="Dogfood"))
    run = service.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="real_project_dogfood", status="running"),
    )
    service.add_event(
        run.run_id,
        AgentEventCreateRequest(
            event_type="tool_blocked",
            status="blocked",
            severity="warning",
            human_message="Negative policy check blocked as expected.",
            payload_sanitized={"reason_code": "source_readonly_write_denied"},
        ),
    )
    service.update_run(run.run_id, AgentRunUpdateRequest(status="completed", validation_status="passed"))

    state = service.session_state("aipinho", session.session_id)

    assert state.latest_run_id == run.run_id
    assert state.latest_status == "completed"
    assert state.active_run is None
    assert state.safety_label == "safe"


def test_events_sequence_and_visibility(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("gemini", AgentSessionCreateRequest(title="Gemini"))
    run = service.create_run("gemini", session.session_id, AgentRunCreateRequest(operation_type="gemini_chat", status="running"))

    first = service.add_event(run.run_id, AgentEventCreateRequest(event_type="started", human_message="Comecou"))
    hidden = service.add_event(run.run_id, AgentEventCreateRequest(event_type="raw_detail", human_message="Oculto", visible_in_timeline=False))
    second = service.add_event(run.run_id, AgentEventCreateRequest(event_type="done", human_message="Terminou"))

    visible = service.list_run_events(run.run_id)
    all_events = service.list_run_events(run.run_id, include_hidden=True)

    assert [event.sequence for event in all_events] == [1, 2, 3, 4]
    assert hidden not in visible
    assert [event.event_id for event in visible] == [first.event_id, second.event_id]
    assert service.session_state("gemini", session.session_id).last_event_id == second.event_id
