from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import (
    AgentEvent,
    AgentEventCreateRequest,
    AgentMessage,
    AgentMessageCreateRequest,
    AgentMessagePublic,
    AgentPollingContract,
    AgentRun,
    AgentRunCreateRequest,
    AgentRunEventsResponse,
    AgentRunUpdateRequest,
    AgentSession,
    AgentSessionCreateRequest,
    AgentSessionState,
    AgentSessionUpdateRequest,
    AgentTimelineResponse,
    MobileAgentViewModel,
)
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_event_bus import EVENT_STATUS_BY_TYPE, MultiAgentEventBus
from aipinho.services.agents.agent_profile_registry_service import AgentProfileRegistryService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_timeline_mapper import AgentEventTimelineMapper
from aipinho.services.codex_agent.codex_agent_store import CodexAgentStore
from aipinho.services.events.event_core import redact_payload
from aipinho.services.gemini_executor.gemini_executor_session_store import GeminiExecutorSessionStore
from aipinho.services.interaction.interaction_core import ChatMessageService, ChatSessionService


STATUS_PRECEDENCE = {
    "blocked": 100,
    "failed": 90,
    "validation_failed": 80,
    "pending_approval": 70,
    "delegation_blocked": 68,
    "delegation_failed": 66,
    "waiting_child_run": 65,
    "delegation_running": 65,
    "pending_validation": 60,
    "policy_denied": 55,
    "applying": 50,
    "running": 40,
    "preview_created": 30,
    "cancelled": 25,
    "completed_with_warnings": 20,
    "completed": 20,
    "idle": 0,
    "created": 0,
    "received": 0,
}

SUCCESS_TERMINAL_STATUSES = {"completed", "completed_with_warnings", "cancelled"}
TERMINAL_OVERRIDE_STATUSES = {"blocked", "failed", "validation_failed"}


def _public_message(message: AgentMessage) -> AgentMessagePublic:
    return AgentMessagePublic(
        message_id=message.message_id,
        session_id=message.session_id,
        agent_id=message.agent_id,
        role=message.role,
        message_kind=message.message_kind,
        content_sanitized=message.content_sanitized,
        created_at=message.created_at,
        run_id=message.run_id,
        event_id=message.event_id,
        artifact_ids=message.artifact_ids,
        visible_in_normal_mode=message.visible_in_normal_mode,
        raw_available=bool(message.raw_ref),
        metadata_sanitized=message.metadata_sanitized,
    )


class AgentSessionKernelService:
    def __init__(
        self,
        profiles: AgentProfileRegistryService | None = None,
        store: AgentSessionStore | None = None,
        event_bus: MultiAgentEventBus | None = None,
        timeline_mapper: AgentEventTimelineMapper | None = None,
    ) -> None:
        self.profiles = profiles or AgentProfileRegistryService()
        self.store = store or AgentSessionStore()
        self.event_bus = event_bus or MultiAgentEventBus(self.store)
        self.timeline_mapper = timeline_mapper or AgentEventTimelineMapper()

    def list_profiles(self, *, enabled: bool | None = None):
        return self.profiles.list_profiles(enabled=enabled)

    def get_profile(self, agent_id: str):
        return self.profiles.get(agent_id)

    def create_session(self, agent_id: str, request: AgentSessionCreateRequest) -> AgentSession:
        profile = self.profiles.require(agent_id)
        if not profile.enabled:
            raise PermissionError("agent_profile_disabled")
        metadata = dict(request.metadata_sanitized)
        if request.project_profile_id:
            metadata.setdefault("project_profile_id", request.project_profile_id)
        session = AgentSession(
            agent_id=agent_id,
            title=(request.title or profile.display_name).strip()[:160],
            active_workspace_id=request.active_workspace_id,
            metadata_sanitized=redact_payload(metadata),
        )
        return self.store.create_session(session)

    def list_sessions(self, agent_id: str, *, include_compat: bool = True) -> list[AgentSession]:
        self.profiles.require(agent_id)
        native = self.store.list_sessions(agent_id=agent_id)
        if not include_compat:
            return sorted(native, key=lambda session: session.updated_at, reverse=True)
        combined = {session.session_id: session for session in native}
        for session in self._compat_sessions(agent_id):
            combined.setdefault(session.session_id, session)
        return sorted(combined.values(), key=lambda session: session.updated_at, reverse=True)

    def get_session(self, agent_id: str, session_id: str, *, include_compat: bool = True) -> AgentSession | None:
        self.profiles.require(agent_id)
        native = self.store.get_session(agent_id, session_id)
        if native is not None:
            return native
        if include_compat:
            return next((session for session in self._compat_sessions(agent_id) if session.session_id == session_id), None)
        return None

    def update_session(self, agent_id: str, session_id: str, request: AgentSessionUpdateRequest) -> AgentSession | None:
        session = self.store.get_session(agent_id, session_id, include_deleted=True)
        if session is None:
            return None
        updates: dict[str, Any] = {"updated_at": utc_now_iso()}
        if request.title is not None:
            title = request.title.strip()
            if not title:
                raise ValueError("agent_session_title_required")
            updates["title"] = title[:160]
        if request.archived is not None:
            updates["archived"] = request.archived
        if request.deleted is not None:
            updates["deleted"] = request.deleted
        if request.active_workspace_id is not None:
            updates["active_workspace_id"] = request.active_workspace_id
        if request.project_profile_id is not None:
            metadata = dict(session.metadata_sanitized)
            metadata["project_profile_id"] = request.project_profile_id
            updates["metadata_sanitized"] = redact_payload(metadata)
        if request.metadata_sanitized is not None:
            metadata = dict(updates.get("metadata_sanitized") or session.metadata_sanitized)
            metadata.update(request.metadata_sanitized)
            updates["metadata_sanitized"] = redact_payload(metadata)
        return self.store.update_session(session.model_copy(update=updates))

    def delete_session(self, agent_id: str, session_id: str) -> AgentSession | None:
        return self.store.soft_delete_session(agent_id, session_id)

    def add_message(self, agent_id: str, session_id: str, request: AgentMessageCreateRequest) -> AgentMessage:
        if self.store.get_session(agent_id, session_id) is None:
            raise FileNotFoundError(session_id)
        message = AgentMessage(
            session_id=session_id,
            agent_id=agent_id,
            role=request.role,
            message_kind=request.message_kind,
            content_sanitized=str(redact_payload(request.content_sanitized)),
            run_id=request.run_id,
            event_id=request.event_id,
            artifact_ids=request.artifact_ids,
            visible_in_normal_mode=request.visible_in_normal_mode,
            raw_ref=request.raw_ref,
            metadata_sanitized=redact_payload(request.metadata_sanitized),
        )
        return self.store.add_message(message)

    def list_messages(self, agent_id: str, session_id: str, *, include_raw_ref: bool = False) -> list[AgentMessage | AgentMessagePublic]:
        native = self.store.list_messages(agent_id, session_id)
        if not native:
            native = self._compat_messages(agent_id, session_id)
        if include_raw_ref:
            return native
        return [_public_message(message) for message in native if message.visible_in_normal_mode]

    def create_run(self, agent_id: str, session_id: str, request: AgentRunCreateRequest) -> AgentRun:
        if self.get_session(agent_id, session_id) is None:
            raise FileNotFoundError(session_id)
        run = AgentRun(
            session_id=session_id,
            agent_id=agent_id,
            parent_run_id=request.parent_run_id,
            delegation_id=request.delegation_id,
            status=request.status,
            operation_type=request.operation_type,
            workspace_id=request.workspace_id,
            project_profile_id=request.project_profile_id,
            workspace_profile_id=request.workspace_profile_id,
            validation_profile_id=request.validation_profile_id,
            command_profile_ids=request.command_profile_ids,
            capabilities_requested=request.capabilities_requested,
            validation_status=request.validation_status,
            artifact_ids=request.artifact_ids,
            memory_refs_used=request.memory_refs_used,
            memory_refs_written=request.memory_refs_written,
            memory_candidates_created=request.memory_candidates_created,
            memory_warnings=request.memory_warnings,
            final_message_id=request.final_message_id,
            error_code=request.error_code,
            metadata_sanitized=redact_payload(request.metadata_sanitized),
        )
        saved = self.store.save_run(run)
        self.event_bus.append_event(
            saved,
            AgentEventCreateRequest(
                event_type="agent_run_created",
                status=saved.status,
                severity="info",
                human_message=f"Run criado para {saved.operation_type}.",
                visible_in_timeline=False,
                payload_sanitized={
                    "operation_type": saved.operation_type,
                    "project_profile_id": saved.project_profile_id,
                    "workspace_profile_id": saved.workspace_profile_id,
                    "validation_profile_id": saved.validation_profile_id,
                    "command_profile_ids": saved.command_profile_ids,
                },
            ),
        )
        return saved

    def get_run(self, run_id: str) -> AgentRun | None:
        return self.store.get_run(run_id)

    def update_run(self, run_id: str, request: AgentRunUpdateRequest) -> AgentRun | None:
        run = self.store.get_run(run_id)
        if run is None:
            return None
        updates = {key: value for key, value in request.model_dump().items() if value is not None}
        if updates.get("status") in {"completed", "completed_with_warnings", "failed", "blocked", "validation_failed", "cancelled"} and "completed_at" not in updates:
            updates["completed_at"] = utc_now_iso()
        if "metadata_sanitized" in updates:
            updates["metadata_sanitized"] = redact_payload(updates["metadata_sanitized"])
        updated = self.store.save_run(run.model_copy(update=updates))
        if request.status is not None:
            event_type = self._event_type_for_run_status(request.status)
            if event_type:
                self.event_bus.append_event(
                    updated,
                    AgentEventCreateRequest(
                        event_type=event_type,
                        status=request.status,
                        severity="error" if request.status in {"failed", "validation_failed"} else "info",
                        human_message=f"Run atualizado para {request.status}.",
                        payload_sanitized={"operation_type": updated.operation_type},
                    ),
                )
        return updated

    def add_event(self, run_id: str, request: AgentEventCreateRequest) -> AgentEvent:
        run = self.store.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        return self.event_bus.append_event(run, request)

    def list_run_events(
        self,
        run_id: str,
        *,
        include_hidden: bool = False,
        after_event_id: str | None = None,
        after_sequence: int | None = None,
        limit: int = 200,
    ) -> list[AgentEvent]:
        return self.event_bus.list_events_by_run(
            run_id,
            include_hidden=include_hidden,
            after_event_id=after_event_id,
            after_sequence=after_sequence,
            limit=limit,
        )

    def run_events_response(
        self,
        run_id: str,
        *,
        after_event_id: str | None = None,
        after_sequence: int | None = None,
        limit: int = 200,
        include_hidden: bool = False,
        mode: str = "normal",
    ) -> AgentRunEventsResponse:
        run = self.store.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        include = include_hidden or mode in {"details", "raw"}
        events = self.list_run_events(run_id, include_hidden=include, after_event_id=after_event_id, after_sequence=after_sequence, limit=limit)
        latest = self.store.list_events(run_id, include_hidden=True, limit=100000)
        latest_event = latest[-1] if latest else None
        return AgentRunEventsResponse(
            run_id=run_id,
            agent_id=run.agent_id,
            session_id=run.session_id,
            latest_event_id=latest_event.event_id if latest_event else None,
            latest_sequence=latest_event.sequence if latest_event else 0,
            status=self._status_with_events(run, latest),
            events=events,
            cards=self.timeline_mapper.map_events(events, mode=mode),
            has_more=len(events) >= limit,
            polling=self._polling_for_status(self._status_with_events(run, latest)),
        )

    def timeline_response(
        self,
        agent_id: str,
        session_id: str,
        *,
        after_event_id: str | None = None,
        after_sequence: int | None = None,
        limit: int = 200,
        include_hidden: bool = False,
        mode: str = "normal",
    ) -> AgentTimelineResponse:
        if self.get_session(agent_id, session_id) is None:
            raise FileNotFoundError(session_id)
        include = include_hidden or mode in {"details", "raw"}
        events = self.event_bus.list_events_by_session(
            agent_id,
            session_id,
            after_event_id=after_event_id,
            after_sequence=after_sequence,
            limit=limit,
            include_hidden=include,
        )
        state = self.session_state(agent_id, session_id)
        latest = self.event_bus.get_latest_event(agent_id, session_id, include_hidden=True)
        polling = self._polling_for_status(state.latest_status)
        messages = self.list_messages(agent_id, session_id, include_raw_ref=False)
        return AgentTimelineResponse(
            agent_id=agent_id,
            session_id=session_id,
            latest_event_id=latest.event_id if latest else None,
            latest_sequence=latest.session_sequence if latest else 0,
            has_more=len(events) >= limit,
            run_status=state.latest_status,
            active_run_id=state.active_run.run_id if state.active_run else None,
            events=events,
            messages=messages,
            cards=self.timeline_mapper.map_events(events, mode=mode),
            polling_recommended=polling.enabled,
            next_poll_seconds=polling.recommended_interval_seconds,
            polling=polling,
        )

    def mobile_view_model(
        self,
        agent_id: str,
        session_id: str,
        *,
        after_event_id: str | None = None,
        mode: str = "normal",
    ) -> MobileAgentViewModel:
        state = self.session_state(agent_id, session_id)
        timeline = self.timeline_response(agent_id, session_id, after_event_id=after_event_id, mode=mode, limit=200)
        return MobileAgentViewModel(
            agent_id=agent_id,
            session_id=session_id,
            state=state,
            messages=timeline.messages,
            events=timeline.cards,
            cards=timeline.cards,
            details={
                "mode": mode,
                "latest_event_id": timeline.latest_event_id,
                "latest_sequence": timeline.latest_sequence,
                "active_run_id": timeline.active_run_id,
            } if mode in {"details", "raw"} else {},
            raw_available=state.raw_available or any(card.raw_available for card in timeline.cards),
            raw_default_visible=False,
            polling=timeline.polling,
            active_run=state.active_run,
        )

    def session_state(self, agent_id: str, session_id: str) -> AgentSessionState:
        session = self.get_session(agent_id, session_id)
        if session is None:
            raise FileNotFoundError(session_id)
        messages = self.list_messages(agent_id, session_id, include_raw_ref=True)
        runs = self.store.list_runs(agent_id=agent_id, session_id=session_id)
        session_events = self.store.list_events_by_session(agent_id, session_id, include_hidden=True)
        selected = self._select_state_run(runs, session_events=session_events)
        run_events = [event for event in session_events if selected and event.run_id == selected.run_id]
        last_event = session_events[-1] if session_events else None
        latest_status = self._status_with_events(selected, run_events) if selected else "idle"
        return AgentSessionState(
            agent_id=agent_id,
            session_id=session_id,
            latest_run_id=selected.run_id if selected else None,
            latest_operation_type=selected.operation_type if selected else None,
            latest_status=latest_status,
            active_run=selected if selected and latest_status not in {"completed", "completed_with_warnings", "cancelled"} else None,
            pending_approval=self._pending_approval_payload(selected, run_events, latest_status),
            validation_status=self._validation_status(selected, run_events),
            artifact_count=sum(len(run.artifact_ids) for run in runs) + sum(len(event.artifact_ids) for event in session_events),
            message_count=len(messages),
            last_event_id=last_event.event_id if last_event else None,
            last_sequence=last_event.session_sequence if last_event else 0,
            safety_label=self._safety_label(latest_status),
            raw_available=any(getattr(message, "raw_ref", None) for message in messages) or any(event.raw_ref for event in session_events),
            blocked_reason_code=self._blocked_reason(run_events),
            updated_at=session.updated_at,
        )

    def _select_state_run(self, runs: list[AgentRun], *, session_events: list[AgentEvent] | None = None) -> AgentRun | None:
        if not runs:
            return None
        session_events = session_events or []
        return sorted(
            runs,
            key=lambda run: (
                STATUS_PRECEDENCE.get(
                    self._status_with_events(run, [event for event in session_events if event.run_id == run.run_id]),
                    10,
                ),
                run.started_at,
            ),
            reverse=True,
        )[0]

    def _status_with_events(self, run: AgentRun | None, events: list[AgentEvent]) -> str:
        base = run.status if run else "idle"
        if base in SUCCESS_TERMINAL_STATUSES:
            run_terminal_events = [
                event.status
                for event in events
                if event.event_type
                in {
                    "agent_run_completed",
                    "agent_run_completed_with_warnings",
                    "agent_run_cancelled",
                    "agent_run_failed",
                    "agent_run_blocked",
                    "validation_failed",
                }
            ]
            if run_terminal_events:
                return run_terminal_events[-1]
            return base
        candidates = [base]
        candidates.extend(event.status for event in events)
        return sorted(candidates, key=lambda status: STATUS_PRECEDENCE.get(status, 10), reverse=True)[0]

    def _validation_status(self, run: AgentRun | None, events: list[AgentEvent]) -> str | None:
        if any(event.status == "validation_failed" for event in events):
            return "validation_failed"
        if any(event.event_type == "validation_passed" for event in events):
            return "passed"
        return run.validation_status if run else None

    def _pending_approval_payload(self, run: AgentRun | None, events: list[AgentEvent], status: str) -> dict[str, Any] | None:
        if run is None or status != "pending_approval":
            return None
        payload: dict[str, Any] = {"run_id": run.run_id}
        approval_id = self._latest_approval_id(events)
        if approval_id:
            payload["approval_id"] = approval_id
        return payload

    def _latest_approval_id(self, events: list[AgentEvent]) -> str | None:
        for event in reversed(events):
            if event.approval_id:
                return event.approval_id
        return None

    def _blocked_reason(self, events: list[AgentEvent]) -> str | None:
        for event in reversed(events):
            if event.status == "blocked":
                reason = event.payload_sanitized.get("reason_code") or event.payload_sanitized.get("block_reason_code")
                return str(reason) if reason else event.event_type
        return None

    def _polling_for_status(self, status: str) -> AgentPollingContract:
        active = status not in {"completed", "completed_with_warnings", "failed", "blocked", "cancelled", "idle"}
        return AgentPollingContract(
            enabled=active,
            recommended_interval_seconds=5,
            reason="active_run" if active else "terminal_or_idle",
        )

    def _event_type_for_run_status(self, status: str) -> str | None:
        return {
            "running": "agent_run_running",
            "waiting_child_run": "delegation_progress",
            "delegation_running": "delegation_progress",
            "completed": "agent_run_completed",
            "completed_with_warnings": "agent_run_completed_with_warnings",
            "failed": "agent_run_failed",
            "blocked": "agent_run_blocked",
            "cancelled": "agent_run_cancelled",
            "pending_approval": "approval_required",
            "pending_validation": "validation_started",
            "validation_failed": "validation_failed",
        }.get(status)

    def _safety_label(self, status: str) -> str:
        if status == "blocked":
            return "blocked"
        if status in {"failed", "validation_failed"}:
            return "attention"
        if status == "pending_approval":
            return "needs_approval"
        return "safe"

    def _compat_sessions(self, agent_id: str) -> list[AgentSession]:
        if agent_id == "aipinho":
            return [
                AgentSession(
                    session_id=session.session_id,
                    agent_id="aipinho",
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    metadata_sanitized={"compat_source": "chat"},
                )
                for session in ChatSessionService().list()
            ]
        if agent_id == "gemini":
            return [
                AgentSession(
                    session_id=session.session_id,
                    agent_id="gemini",
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    metadata_sanitized={"compat_source": "gemini_executor", "provider": "gemini"},
                )
                for session in GeminiExecutorSessionStore().list()
            ]
        if agent_id == "codex":
            return [
                AgentSession(
                    session_id=session.session_id,
                    agent_id="codex",
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    archived=session.archived,
                    deleted=session.deleted,
                    active_workspace_id=session.active_workspace_id,
                    metadata_sanitized={"compat_source": "codex_agent"},
                )
                for session in CodexAgentStore().list()
            ]
        return []

    def _compat_messages(self, agent_id: str, session_id: str) -> list[AgentMessage]:
        if agent_id == "aipinho" and ChatSessionService().get(session_id) is not None:
            mapped = []
            for message in ChatMessageService().list(session_id=session_id):
                role = message.role if message.role in {"user", "assistant"} else "status"
                mapped.append(AgentMessage(
                    message_id=message.message_id,
                    session_id=session_id,
                    agent_id="aipinho",
                    role=role,
                    message_kind="chat_message",
                    content_sanitized=message.content,
                    created_at=message.created_at,
                    event_id=message.source_event_id,
                    raw_ref=message.raw_ref,
                    metadata_sanitized={"compat_source": "chat", **message.metadata},
                ))
            return mapped
        if agent_id == "gemini" and GeminiExecutorSessionStore().get(session_id) is not None:
            return [
                AgentMessage(
                    message_id=message.message_id,
                    session_id=session_id,
                    agent_id="gemini",
                    role=message.role if message.role in {"user", "assistant"} else "status",
                    message_kind="chat_message",
                    content_sanitized=message.content,
                    created_at=message.created_at,
                    metadata_sanitized={"compat_source": "gemini_executor", **message.metadata},
                )
                for message in GeminiExecutorSessionStore().messages(session_id)
            ]
        if agent_id == "codex" and CodexAgentStore().get(session_id) is not None:
            return [
                AgentMessage(
                    message_id=message.message_id,
                    session_id=session_id,
                    agent_id="codex",
                    role=message.role if message.role in {"user", "assistant", "tool", "status", "error"} else "status",
                    message_kind="chat_message" if message.message_kind == "chat" else "run_status",
                    content_sanitized=message.content,
                    created_at=message.created_at,
                    run_id=message.run_id,
                    event_id=message.event_id,
                    artifact_ids=[],
                    metadata_sanitized={"compat_source": "codex_agent", **message.metadata},
                )
                for message in CodexAgentStore().messages(session_id)
            ]
        return []
