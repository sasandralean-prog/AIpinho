from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso

ChatMessageRole = Literal["user", "assistant", "speaker", "system", "debugger"]
FeedbackRating = Literal["like", "dislike", "neutral"]


class ChatSessionCreateRequest(AIpinhoModel):
    title: str | None = None
    client_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSessionRenameRequest(AIpinhoModel):
    title: str


class ChatSessionRecord(AIpinhoModel):
    session_id: str = Field(default_factory=lambda: f"chat_{uuid4().hex}")
    title: str = "Nova conversa"
    client_id: str | None = None
    status: str = "active"
    message_count: int = 0
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessageCreateRequest(AIpinhoModel):
    role: ChatMessageRole = "user"
    content: str
    source_event_id: str | None = None
    task_id: str | None = None
    raw_payload: dict[str, Any] | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessageRecord(AIpinhoModel):
    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex}")
    session_id: str
    role: ChatMessageRole
    content: str
    source_event_id: str | None = None
    task_id: str | None = None
    raw_ref: str | None = None
    raw_available: bool = False
    chunk_index: int = 1
    chunk_total: int = 1
    copy_allowed: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatTimeline(AIpinhoModel):
    session_id: str
    messages: list[ChatMessageRecord] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    cursor: str | None = None


class CopyPayload(AIpinhoModel):
    item_id: str
    text: str
    sanitized: bool = True


class RawPayloadResponse(AIpinhoModel):
    raw_ref: str
    raw: dict[str, Any] | str
    warning: str = "raw_tecnico_sob_demanda"


class FeedbackRequest(AIpinhoModel):
    target_type: str
    target_id: str
    rating: FeedbackRating
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackRecord(AIpinhoModel):
    feedback_id: str = Field(default_factory=lambda: f"feedback_{uuid4().hex}")
    target_type: str
    target_id: str
    rating: FeedbackRating
    reason: str | None = None
    evaluation_signal_created: bool = True
    regression_candidate_created: bool = True
    auto_memory_mutation: bool = False
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SpeakerTruthRequest(AIpinhoModel):
    source_event_id: str
    requested_message: str | None = None


class SpeakerTruthResult(AIpinhoModel):
    allowed: bool
    source_event_id: str
    message: str
    reasons: list[str] = Field(default_factory=list)


class TaskCard(AIpinhoModel):
    task_id: str
    status: str
    phase: str | None = None
    human_summary: str
    active_error: str | None = None
    approvals_pending: int = 0
    active_patch_id: str | None = None
    updated_at: str = Field(default_factory=utc_now_iso)


class PipelineStageCard(AIpinhoModel):
    stage_id: str
    task_id: str
    role: str
    status: str
    human_summary: str
    severity: str = "info"
    updated_at: str = Field(default_factory=utc_now_iso)


class PipelineCard(AIpinhoModel):
    task_id: str
    stages: list[PipelineStageCard] = Field(default_factory=list)
