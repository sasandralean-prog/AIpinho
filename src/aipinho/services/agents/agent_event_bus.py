from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import AgentEvent, AgentEventCreateRequest, AgentRun
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.events.event_core import redact_payload


EVENT_STATUS_BY_TYPE = {
    "agent_run_created": "created",
    "agent_run_started": "running",
    "agent_run_planning": "running",
    "agent_run_waiting": "running",
    "agent_run_running": "running",
    "agent_run_completed": "completed",
    "agent_run_completed_with_warnings": "completed_with_warnings",
    "agent_run_failed": "failed",
    "agent_run_blocked": "blocked",
    "agent_run_cancelled": "cancelled",
    "approval_required": "pending_approval",
    "approval_granted": "running",
    "approval_denied": "blocked",
    "auto_approval_granted": "running",
    "auto_approval_denied": "blocked",
    "preview_created": "preview_created",
    "apply_started": "applying",
    "apply_finished": "pending_validation",
    "validation_started": "pending_validation",
    "validation_step": "pending_validation",
    "validation_passed": "completed",
    "validation_failed": "validation_failed",
    "policy_check_started": "running",
    "policy_check_completed": "running",
    "policy_decision_allow": "running",
    "policy_decision_auto_approve": "running",
    "policy_decision_require_approval": "pending_approval",
    "policy_decision_deny": "blocked",
    "auto_approval_granted": "running",
    "auto_approval_denied": "blocked",
    "operation_blocked": "blocked",
    "safe_alternative_available": "blocked",
    "delegation_created": "running",
    "delegation_policy_check_started": "running",
    "delegation_policy_check_completed": "running",
    "delegation_auto_approved": "running",
    "delegation_approval_required": "pending_approval",
    "delegation_rejected": "blocked",
    "delegation_accepted": "delegation_running",
    "delegation_child_session_created": "delegation_running",
    "delegation_child_run_created": "delegation_running",
    "delegation_child_run_started": "delegation_running",
    "delegation_child_event": "delegation_running",
    "delegation_progress": "delegation_running",
    "delegation_completed": "completed",
    "delegation_completed_with_warnings": "completed_with_warnings",
    "delegation_failed": "failed",
    "delegation_blocked": "blocked",
    "delegation_cancelled": "cancelled",
    "delegation_timed_out": "failed",
    "memory_search_started": "running",
    "memory_search_completed": "running",
    "memory_context_loaded": "running",
    "memory_context_attached_to_delegation": "delegation_running",
    "memory_candidate_created": "running",
    "memory_candidate_accepted": "running",
    "memory_candidate_rejected": "running",
    "memory_written": "running",
    "memory_updated": "running",
    "memory_superseded": "running",
    "memory_contradiction_detected": "running",
    "memory_marked_stale": "running",
    "memory_access_denied": "blocked",
    "memory_validation_started": "running",
    "memory_validation_passed": "running",
    "memory_validation_failed": "failed",
}


class MultiAgentEventBus:
    def __init__(self, store: AgentSessionStore | None = None) -> None:
        self.store = store or AgentSessionStore()

    def append_event(self, run: AgentRun, request: AgentEventCreateRequest) -> AgentEvent:
        status = request.status
        if status == "received":
            status = EVENT_STATUS_BY_TYPE.get(request.event_type, status)
        event = AgentEvent(
            run_id=run.run_id,
            session_id=run.session_id,
            agent_id=run.agent_id,
            event_type=request.event_type,
            status=status,
            severity=request.severity,
            human_message=str(redact_payload(request.human_message)),
            technical_summary_sanitized=str(redact_payload(request.technical_summary_sanitized)) if request.technical_summary_sanitized is not None else None,
            payload_sanitized=redact_payload(request.payload_sanitized),
            visible_in_timeline=request.visible_in_timeline,
            evidence_refs=request.evidence_refs,
            parent_event_id=request.parent_event_id,
            correlation_id=request.correlation_id,
            tool_invocation_id=request.tool_invocation_id,
            delegation_id=request.delegation_id,
            approval_id=request.approval_id,
            validation_id=request.validation_id,
            artifact_ids=request.artifact_ids,
            progress_current=request.progress_current,
            progress_total=request.progress_total,
            raw_ref=request.raw_ref,
        )
        return self.store.add_event(event)

    def append_status_event(self, run: AgentRun, event_type: str, message: str, **payload: Any) -> AgentEvent:
        return self.append_event(
            run,
            AgentEventCreateRequest(
                event_type=event_type,
                status=EVENT_STATUS_BY_TYPE.get(event_type, "running"),
                severity="info",
                human_message=message,
                payload_sanitized=payload,
            ),
        )

    def append_error_event(self, run: AgentRun, event_type: str, message: str, *, error_code: str | None = None) -> AgentEvent:
        payload: dict[str, Any] = {}
        if error_code:
            payload["error_code"] = error_code
        return self.append_event(
            run,
            AgentEventCreateRequest(
                event_type=event_type,
                status=EVENT_STATUS_BY_TYPE.get(event_type, "failed"),
                severity="error",
                human_message=message,
                payload_sanitized=payload,
            ),
        )

    def list_events_by_run(
        self,
        run_id: str,
        *,
        after_event_id: str | None = None,
        after_sequence: int | None = None,
        limit: int = 200,
        include_hidden: bool = False,
    ) -> list[AgentEvent]:
        events = self.store.list_events(run_id, limit=100000, include_hidden=include_hidden)
        return self._apply_cursor(events, after_event_id=after_event_id, after_sequence=after_sequence, limit=limit, sequence_attr="sequence")

    def list_events_by_session(
        self,
        agent_id: str,
        session_id: str,
        *,
        after_event_id: str | None = None,
        after_sequence: int | None = None,
        limit: int = 200,
        include_hidden: bool = False,
    ) -> list[AgentEvent]:
        events = self.store.list_events_by_session(agent_id, session_id, include_hidden=include_hidden)
        return self._apply_cursor(events, after_event_id=after_event_id, after_sequence=after_sequence, limit=limit, sequence_attr="session_sequence")

    def get_latest_event(self, agent_id: str, session_id: str, *, include_hidden: bool = True) -> AgentEvent | None:
        events = self.store.list_events_by_session(agent_id, session_id, include_hidden=include_hidden)
        return events[-1] if events else None

    def get_last_sequence(self, agent_id: str, session_id: str) -> int:
        latest = self.get_latest_event(agent_id, session_id)
        return latest.session_sequence if latest else 0

    def _apply_cursor(
        self,
        events: list[AgentEvent],
        *,
        after_event_id: str | None,
        after_sequence: int | None,
        limit: int,
        sequence_attr: str,
    ) -> list[AgentEvent]:
        selected = events
        if after_event_id:
            indexes = [index for index, event in enumerate(selected) if event.event_id == after_event_id]
            if not indexes:
                return []
            selected = selected[indexes[-1] + 1 :]
        if after_sequence is not None:
            selected = [event for event in selected if int(getattr(event, sequence_attr)) > after_sequence]
        return selected[: max(1, min(limit, 1000))]
