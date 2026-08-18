from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from aipinho.schemas.chat.chat_message import ChatMessage
from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.session_event import SessionEvent
from aipinho.schemas.chat.session_state import SessionState
from aipinho.services.session.session_event_service import SessionEventService
from aipinho.services.session.session_policy_service import SessionPolicyService
from aipinho.services.session.session_redaction_service import SessionRedactionService
from aipinho.services.session.session_state_reconciliation_service import SessionStateReconciliationService
from aipinho.services.session.session_store import SessionStore, utc_now


def _dump_model(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


class SessionService:
    def __init__(
        self,
        store: SessionStore | None = None,
        policy: SessionPolicyService | None = None,
        redaction: SessionRedactionService | None = None,
        event_service: SessionEventService | None = None,
    ) -> None:
        self.store = store or SessionStore()
        self.policy = policy or SessionPolicyService().load()
        self.redaction = redaction or SessionRedactionService().load()
        self.event_service = event_service or SessionEventService()
        self.reconciliation = SessionStateReconciliationService(policy=self.policy)

    def create_session(self, surface: str | None = None, session_id: str | None = None) -> SessionState:
        now = datetime.now(timezone.utc)
        resolved_session_id = session_id or f"session_{uuid4().hex}"
        if not re.fullmatch(r"(?:session|chat)_[A-Za-z0-9_-]+", resolved_session_id):
            raise ValueError("invalid_session_id")
        state = SessionState(
            session_id=resolved_session_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=self.policy.ttl_minutes())).isoformat(),
            surface=surface or "unknown",
        )
        self.store.save(state)
        self.append_event(state.session_id, "session_created", "Sessao criada.")
        return state

    def get_session(self, session_id: str) -> SessionState | None:
        state = self.store.get(session_id)
        if state is None:
            return None
        state, reasons = self.reconciliation.reconcile(state)
        if reasons:
            state.warnings = list(dict.fromkeys([*state.warnings, *reasons]))
            self.store.save(state)
        return state

    def ensure_session(self, request: ChatRequest) -> SessionState:
        if request.session_id:
            existing = self.get_session(request.session_id)
            if existing is not None and existing.status == "active":
                return existing
        surface = request.context.surface if request.context else "api"
        return self.create_session(surface=surface, session_id=request.session_id)

    def delete_session(self, session_id: str) -> bool:
        self.append_event(session_id, "session_deleted", "Sessao removida.") if self.get_session(session_id) else None
        return self.store.delete(session_id)

    def append_event(self, session_id: str, event_type, summary: str, data: dict | None = None, warnings: list[str] | None = None) -> SessionEvent:
        event = self.event_service.create(session_id=session_id, event_type=event_type, summary=summary, data=data or {}, warnings=warnings or [])
        self.store.append_event(event)
        return event

    def list_events(self, session_id: str) -> list[SessionEvent]:
        return self.store.list_events(session_id)

    def update_after_chat(
        self,
        state: SessionState,
        request: ChatRequest,
        intent_map: Any,
        policy_decision: Any,
        *,
        task_draft_id: str | None = None,
        status: str = "ok",
    ) -> SessionState:
        sanitized = self.redaction.sanitize_message(request.message, max_chars=self.policy.max_message_chars())
        recent = list(state.recent_messages)
        recent.append(ChatMessage(role="user", content=sanitized))
        recent = recent[-self.policy.max_recent_messages():]
        workspace_candidate = state.active_workspace_candidate
        workspace = getattr(intent_map, "workspace", None)
        if workspace is not None and getattr(workspace, "declared", False) and not getattr(workspace, "protected", False):
            workspace_candidate = getattr(workspace, "path", None)
        if workspace is not None and getattr(workspace, "protected", False) and not self.policy.forbidden_root_as_active_workspace():
            workspace_candidate = state.active_workspace_candidate
        now = utc_now()
        state = SessionState(
            session_id=state.session_id,
            status=state.status,
            created_at=state.created_at,
            updated_at=now,
            expires_at=state.expires_at,
            surface=state.surface,
            recent_messages=recent,
            last_intent_map=self._intent_summary(intent_map),
            last_policy_decision=self._policy_summary(policy_decision),
            active_workspace_candidate=workspace_candidate,
            active_task_draft_id=task_draft_id or state.active_task_draft_id,
            last_operational_context=dict(state.last_operational_context),
            warnings=list(dict.fromkeys([*state.warnings, *getattr(intent_map, "warnings", [])])),
            trace_refs=state.trace_refs,
        )
        self.store.save(state)
        self.append_event(
            state.session_id,
            "chat_message",
            f"Mensagem processada com status {status}.",
            data={"intent_type": getattr(intent_map, "intent_type", "unknown"), "task_draft_id": task_draft_id},
        )
        return state

    def record_operational_context(self, session_id: str, context: dict[str, Any]) -> SessionState | None:
        state = self.get_session(session_id)
        if state is None:
            return None
        allowed = {
            "operation_type",
            "path",
            "workspace",
            "run_id",
            "artifact_id",
            "updated_at",
        }
        sanitized = {
            key: str(value)[:1000]
            for key, value in (context or {}).items()
            if key in allowed and value is not None
        }
        if not sanitized:
            return state
        state = state.model_copy(update={"last_operational_context": sanitized, "updated_at": utc_now()})
        self.store.save(state)
        self.append_event(
            state.session_id,
            "operational_context_updated",
            "Contexto operacional recente atualizado.",
            data={"operation_type": sanitized.get("operation_type"), "path": sanitized.get("path")},
        )
        return state

    def _intent_summary(self, intent_map: Any) -> dict[str, Any]:
        if intent_map is None:
            return {}
        workspace = getattr(intent_map, "workspace", None)
        return {
            "intent_id": getattr(intent_map, "intent_id", None),
            "intent_type": getattr(intent_map, "intent_type", "unknown"),
            "task_type": getattr(intent_map, "task_type", "none"),
            "requires_task": getattr(intent_map, "requires_task", False),
            "requires_workspace": getattr(intent_map, "requires_workspace", False),
            "workspace": {
                "path": getattr(workspace, "path", None),
                "declared": getattr(workspace, "declared", False),
                "protected": getattr(workspace, "protected", False),
            },
        }

    def _policy_summary(self, policy_decision: Any) -> dict[str, Any]:
        if policy_decision is None:
            return {}
        return {
            "status": getattr(policy_decision, "status", "unknown"),
            "contract_type": getattr(policy_decision, "contract_type", "unknown"),
            "allowed_actions": list(getattr(policy_decision, "allowed_actions", [])),
            "denied_actions": list(getattr(policy_decision, "denied_actions", [])),
            "approval_required_for": list(getattr(policy_decision, "approval_required_for", [])),
            "safe_to_execute": bool(getattr(policy_decision, "safe_to_execute", False)),
            "safe_to_preview": bool(getattr(policy_decision, "safe_to_preview", False)),
        }

    def status(self) -> dict[str, object]:
        policy_status = self.policy.status()
        store_status = self.store.status()
        redaction_status = self.redaction.status()
        overall = "ok" if policy_status.get("status") == store_status.get("status") == redaction_status.get("status") == "ok" else "degraded"
        return {"status": overall, "service": "session", "policy": policy_status, "store": store_status, "redaction": redaction_status}
