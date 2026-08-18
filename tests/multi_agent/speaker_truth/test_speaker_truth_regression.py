from __future__ import annotations

import pytest

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentMessageCreateRequest, AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore


def _service(tmp_path):
    return AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))


def _run_with_final(service, agent_id: str, *, status: str, evidence_refs: list[str], validation_status: str | None = None):
    session = service.create_session(agent_id, AgentSessionCreateRequest(title="Truth"))
    run = service.create_run(agent_id, session.session_id, AgentRunCreateRequest(operation_type="truth_check", status="running", validation_status=validation_status))
    final = service.add_message(agent_id, session.session_id, AgentMessageCreateRequest(role="assistant", message_kind="final_answer", content_sanitized="Concluido com evidencia.", run_id=run.run_id))
    service.add_event(run.run_id, AgentEventCreateRequest(event_type="final_answer_created", status=status, human_message="Resposta final gerada.", evidence_refs=evidence_refs, validation_id="validation_ok" if validation_status == "passed" else None))
    service.update_run(run.run_id, AgentRunUpdateRequest(status=status, final_message_id=final.message_id, validation_status=validation_status))
    return session, run


@pytest.mark.multi_agent
@pytest.mark.speaker_truth
def test_completed_claim_requires_final_message_event_and_evidence(tmp_path):
    service = _service(tmp_path)
    _, run = _run_with_final(service, "aipinho", status="completed", evidence_refs=["tool:read_file", "artifact:report"], validation_status="passed")

    events = service.list_run_events(run.run_id)
    stored = service.get_run(run.run_id)

    assert stored.status == "completed"
    assert stored.validation_status == "passed"
    assert stored.final_message_id
    assert any(event.event_type == "final_answer_created" and event.evidence_refs for event in events)


@pytest.mark.multi_agent
@pytest.mark.speaker_truth
def test_validation_failed_and_blocked_are_not_clean_completed(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("codex", AgentSessionCreateRequest(title="Failure truth"))
    failed = service.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="validation", status="validation_failed", validation_status="failed"))
    blocked = service.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="policy", status="blocked", error_code="source_readonly_write_denied"))

    state = service.session_state("codex", session.session_id)

    assert failed.status != "completed"
    assert blocked.status != "completed"
    assert state.latest_status == "blocked"


@pytest.mark.multi_agent
@pytest.mark.speaker_truth
def test_optimistic_success_without_evidence_is_detectable_by_contract(tmp_path):
    service = _service(tmp_path)
    session = service.create_session("gemini", AgentSessionCreateRequest(title="Optimistic"))
    run = service.create_run("gemini", session.session_id, AgentRunCreateRequest(operation_type="artifact_generation", status="completed"))
    service.add_message("gemini", session.session_id, AgentMessageCreateRequest(role="assistant", message_kind="final_answer", content_sanitized="Arquivo criado.", run_id=run.run_id))

    events = service.list_run_events(run.run_id, include_hidden=True)
    has_evidence = any(event.evidence_refs or event.artifact_ids or event.tool_invocation_id or event.validation_id for event in events)

    assert run.status == "completed"
    assert has_evidence is False

