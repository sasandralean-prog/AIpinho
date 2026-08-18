from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.schemas.interaction.contracts import (
    ChatMessageCreateRequest,
    ChatMessageRecord,
    ChatSessionCreateRequest,
    ChatSessionRecord,
    ChatTimeline,
    CopyPayload,
    FeedbackRecord,
    FeedbackRequest,
    PipelineCard,
    PipelineStageCard,
    RawPayloadResponse,
    SpeakerTruthResult,
    TaskCard,
)
from aipinho.services.events.event_core import EventPublisherService, EventRawPayloadStore, EventStoreRepository, redact_payload
from aipinho.utils.yaml_loader import load_yaml_file


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists() or path.stat().st_size == 0:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class ResponseChunkService:
    def __init__(self, chunk_size: int = 1800) -> None:
        self.chunk_size = chunk_size

    def chunk_meta(self, text: str) -> tuple[int, int]:
        total = max(1, (len(text) + self.chunk_size - 1) // self.chunk_size)
        return 1, total


class ChatSessionService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "interaction" / "chat_sessions" / "sessions.json"

    def create(self, request: ChatSessionCreateRequest) -> ChatSessionRecord:
        sessions = self.list()
        record = ChatSessionRecord(title=request.title or "Nova conversa", client_id=request.client_id, metadata=request.metadata)
        sessions.append(record)
        _json_write(self.path, [_dump_model(item) for item in sessions])
        EventPublisherService().publish(EventPublishRequest(
            event_type="chat_session_created",
            source_service="chat",
            human_summary=f"Sessao de chat criada: {record.title}",
            payload={"session_id": record.session_id, "client_id": record.client_id},
        ))
        return record

    def list(self) -> list[ChatSessionRecord]:
        return [ChatSessionRecord(**item) for item in _json_read(self.path, [])]

    def get(self, session_id: str) -> ChatSessionRecord | None:
        for session in self.list():
            if session.session_id == session_id:
                return session
        return None

    def rename(self, session_id: str, title: str) -> ChatSessionRecord | None:
        clean_title = str(title or "").strip()
        if not clean_title:
            raise ValueError("chat_session_title_required")
        sessions = self.list()
        updated: ChatSessionRecord | None = None
        from aipinho.schemas.events.contracts import utc_now_iso

        for session in sessions:
            if session.session_id == session_id:
                session.title = clean_title[:120]
                session.updated_at = utc_now_iso()
                updated = session
                break
        if updated is None:
            return None
        _json_write(self.path, [_dump_model(item) for item in sessions])
        EventPublisherService().publish(EventPublishRequest(
            event_type="chat_session_renamed",
            source_service="chat",
            human_summary=f"Sessao de chat renomeada: {updated.title}",
            payload={"session_id": updated.session_id},
        ))
        return updated

    def delete(self, session_id: str) -> bool:
        sessions = self.list()
        kept = [session for session in sessions if session.session_id != session_id]
        if len(kept) == len(sessions):
            return False
        _json_write(self.path, [_dump_model(item) for item in kept])
        EventPublisherService().publish(EventPublishRequest(
            event_type="chat_session_deleted",
            source_service="chat",
            human_summary="Sessao de chat removida da lista de conversas.",
            payload={"session_id": session_id},
        ))
        return True

    def touch(self, session_id: str) -> None:
        sessions = self.list()
        for session in sessions:
            if session.session_id == session_id:
                session.message_count += 1
                from aipinho.schemas.events.contracts import utc_now_iso
                session.updated_at = utc_now_iso()
        _json_write(self.path, [_dump_model(item) for item in sessions])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "sessions": len(self.list()), "persistent": True}


class ChatMessageService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "interaction" / "messages" / "messages.jsonl"
        self.raw_store = EventRawPayloadStore(PATHS.project_root / "data" / "runtime" / "interaction" / "raw")

    def _append(self, message: ChatMessageRecord) -> ChatMessageRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(message), ensure_ascii=True) + "\n")
        ChatSessionService().touch(message.session_id)
        return message

    def list(self, session_id: str | None = None, limit: int = 200) -> list[ChatMessageRecord]:
        if not self.path.exists():
            return []
        rows: list[ChatMessageRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    record = ChatMessageRecord(**json.loads(line))
                    if session_id is None or record.session_id == session_id:
                        rows.append(record)
        return rows[-limit:]

    def delete_for_session(self, session_id: str) -> int:
        if not self.path.exists():
            return 0
        kept: list[str] = []
        removed = 0
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    kept.append(line.rstrip("\n"))
                    continue
                if not isinstance(payload, dict):
                    kept.append(json.dumps(payload, ensure_ascii=True))
                    continue
                if str(payload.get("session_id") or "") == session_id:
                    removed += 1
                    continue
                try:
                    record = ChatMessageRecord(**payload)
                    kept.append(json.dumps(_dump_model(record), ensure_ascii=True))
                except Exception:
                    kept.append(json.dumps(payload, ensure_ascii=True))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for line in kept:
                handle.write(line + "\n")
        return removed

    def get(self, message_id: str) -> ChatMessageRecord | None:
        for message in self.list(limit=10000):
            if message.message_id == message_id:
                return message
        return None

    def create(self, session_id: str, request: ChatMessageCreateRequest) -> ChatMessageRecord:
        if ChatSessionService().get(session_id) is None:
            raise FileNotFoundError(session_id)
        chunk_index, chunk_total = ResponseChunkService().chunk_meta(request.content)
        raw_ref = None
        if request.raw_payload is not None:
            raw_ref = self.raw_store.store(f"message_{session_id}", request.raw_payload)
        content = str(redact_payload(request.content))
        record = ChatMessageRecord(
            session_id=session_id,
            role=request.role,
            content=content,
            source_event_id=request.source_event_id,
            task_id=request.task_id,
            raw_ref=raw_ref,
            raw_available=bool(raw_ref),
            chunk_index=chunk_index,
            chunk_total=chunk_total,
            metadata=request.metadata,
        )
        self._append(record)
        EventPublisherService().publish(EventPublishRequest(
            event_type="chat_message_created",
            source_service="chat",
            human_summary="Mensagem de chat registrada.",
            payload={"session_id": session_id, "message_id": record.message_id, "role": record.role},
            raw_payload=request.raw_payload,
        ))
        return record

    def copy(self, message_id: str) -> CopyPayload:
        message = self.get(message_id)
        if message is None:
            raise FileNotFoundError(message_id)
        return CopyPayload(item_id=message_id, text=message.content, sanitized=True)


class ChatTimelineService:
    def timeline(self, session_id: str) -> ChatTimeline:
        messages = ChatMessageService().list(session_id=session_id)
        events = []
        event_store = EventStoreRepository()
        for event in event_store.list(limit=200):
            if event.payload.get("session_id") == session_id:
                events.append(redact_payload(_dump_model(event)))
        return ChatTimeline(session_id=session_id, messages=messages, events=events, cursor=event_store.cursor())


class SanitizedRawService:
    def read(self, raw_ref: str) -> RawPayloadResponse:
        payload = EventRawPayloadStore(PATHS.project_root / "data" / "runtime" / "interaction" / "raw").read(raw_ref)
        return RawPayloadResponse(raw_ref=raw_ref, raw=redact_payload(payload.get("raw")))


class CopyActionService:
    def copy_raw(self, raw_ref: str) -> CopyPayload:
        payload = SanitizedRawService().read(raw_ref)
        return CopyPayload(item_id=raw_ref, text=json.dumps(payload.raw, indent=2, ensure_ascii=True), sanitized=True)


class SpeakerTruthService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "interaction" / "speaker_truth_policy.yaml"

    def _policy(self) -> dict[str, Any]:
        return load_yaml_file(self.path, root=PATHS.project_root)

    def _templates(self) -> dict[str, str]:
        data = self._policy()
        return {str(k): str(v) for k, v in data.get("event_templates", {}) or data.get("claims", {}).items()}

    def _has_completion_claim(self, text: str) -> bool:
        lowered = text.lower()
        conservative_negations = ("nao apliquei", "nao corrigi", "nao conclui", "nao alterei", "sem aplicar", "sem alterar")
        if any(negation in lowered for negation in conservative_negations):
            return False
        claims = ("apliquei", "corrigi", "conclui", "concluido", "patch aplicado", "alterei", "arquivo alterado")
        return any(claim in lowered for claim in claims)

    def from_event(self, source_event_id: str, requested_message: str | None = None) -> SpeakerTruthResult:
        event = EventStoreRepository().get(source_event_id)
        if event is None:
            return SpeakerTruthResult(allowed=False, source_event_id=source_event_id, message="Nao encontrei evento fonte para narrar.", reasons=["source_event_not_found"])
        if not event.speaker_allowed:
            return SpeakerTruthResult(allowed=False, source_event_id=source_event_id, message="Este evento nao pode ser narrado no chat.", reasons=["speaker_not_allowed_for_event"])
        message = requested_message or self._templates().get(event.event_type) or event.human_summary
        policy = self._policy()
        truth_policy = policy.get("speaker_truth", {}) if isinstance(policy.get("speaker_truth"), dict) else {}
        completion_events = {str(item) for item in truth_policy.get("completion_events", []) or []}
        if self._has_completion_claim(message) and event.event_type not in completion_events:
            return SpeakerTruthResult(allowed=False, source_event_id=source_event_id, message="Ainda nao tenho evento de conclusao para afirmar isso.", reasons=["completion_claim_without_event"])
        return SpeakerTruthResult(allowed=True, source_event_id=source_event_id, message=str(redact_payload(message)), reasons=[])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "event_sourced": True, "templates": len(self._templates())}


class SpeakerMessageService:
    def create_from_event(self, session_id: str, event_id: str, requested_message: str | None = None) -> ChatMessageRecord:
        result = SpeakerTruthService().from_event(event_id, requested_message)
        if not result.allowed:
            raise PermissionError(",".join(result.reasons))
        return ChatMessageService().create(session_id, ChatMessageCreateRequest(role="speaker", content=result.message, source_event_id=event_id))


class FeedbackService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "interaction" / "feedback" / "feedback.jsonl"

    def create(self, request: FeedbackRequest) -> FeedbackRecord:
        record = FeedbackRecord(**_dump_model(request))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(record), ensure_ascii=True) + "\n")
        EventPublisherService().publish(EventPublishRequest(
            event_type="feedback_created",
            source_service="feedback",
            human_summary="Feedback registrado como sinal de avaliacao, sem alterar memoria automaticamente.",
            payload={"feedback_id": record.feedback_id, "target_type": record.target_type, "target_id": record.target_id, "rating": record.rating},
        ))
        return record

    def list(self, limit: int = 100) -> list[FeedbackRecord]:
        if not self.path.exists():
            return []
        rows: list[FeedbackRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(FeedbackRecord(**json.loads(line)))
        return rows[-limit:]


class TaskSyncService:
    def list_cards(self) -> list[TaskCard]:
        cards: dict[str, TaskCard] = {}
        for event in EventStoreRepository().list(limit=500):
            if event.event_type == "task_card_created":
                task_id = str(event.payload.get("task_id", event.correlation_id or event.event_id))
                cards[task_id] = TaskCard(
                    task_id=task_id,
                    status=str(event.payload.get("status", event.status)),
                    phase=event.payload.get("phase"),
                    human_summary=event.human_summary,
                    active_error=event.payload.get("active_error"),
                    approvals_pending=int(event.payload.get("approvals_pending", 0) or 0),
                    active_patch_id=event.payload.get("active_patch_id"),
                    updated_at=event.created_at,
                )
        return list(cards.values())

    def timeline(self, task_id: str) -> list[dict[str, Any]]:
        return [redact_payload(_dump_model(event)) for event in EventStoreRepository().list(limit=500) if event.payload.get("task_id") == task_id or event.correlation_id == task_id]


class PipelineSyncService:
    def card(self, task_id: str) -> PipelineCard:
        stages: list[PipelineStageCard] = []
        for event in EventStoreRepository().list(limit=500):
            if event.event_type == "pipeline_stage_changed" and event.payload.get("task_id") == task_id:
                stages.append(PipelineStageCard(
                    stage_id=str(event.payload.get("stage_id", event.event_id)),
                    task_id=task_id,
                    role=str(event.payload.get("role", event.source_service)),
                    status=str(event.payload.get("status", event.status)),
                    human_summary=event.human_summary,
                    severity=event.severity,
                    updated_at=event.created_at,
                ))
        return PipelineCard(task_id=task_id, stages=stages)


class InteractionCockpitStatusService:
    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "chat_persistence": True,
            "raw_hidden_by_default": True,
            "speaker_event_sourced": True,
            "auto_model_execution_from_chat": False,
            "auto_patch_from_chat": False,
            "task_cards": len(TaskSyncService().list_cards()),
            "event_cursor": EventStoreRepository().cursor(),
            "context_kernel_enabled": True,
            "context_admission_owner": "context_kernel",
            "chat_builds_final_context": False,
        }
