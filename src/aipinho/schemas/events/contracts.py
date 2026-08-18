from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

EventVisibility = str
EventSeverity = str
EventStatus = str
EventCopyPolicy = str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class EventContractDefinition(AIpinhoModel):
    event_type: str
    required_fields: list[str] = Field(default_factory=list)
    allowed_sources: list[str] = Field(default_factory=list)
    default_visibility: EventVisibility = "timeline"
    default_severity: EventSeverity = "info"
    default_status: EventStatus = "received"
    copy_policy: EventCopyPolicy = "copy_sanitized_only"
    speaker_allowed: bool = True


class EventContractRegistryStatus(AIpinhoModel):
    status: str
    contracts_loaded: int
    unknown_event_default: str
    missing_human_summary_default: str


class EventPublishRequest(AIpinhoModel):
    event_type: str
    source_service: str
    human_summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: EventSeverity | None = None
    status: EventStatus | None = None
    visibility: EventVisibility | None = None
    copy_policy: EventCopyPolicy | None = None
    correlation_id: str | None = None
    source_event_id: str | None = None
    raw_payload: dict[str, Any] | str | None = None


class EventValidationResult(AIpinhoModel):
    allowed: bool
    event_type: str
    reasons: list[str] = Field(default_factory=list)
    contract: EventContractDefinition | None = None


class StoredEvent(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"event_{uuid4().hex}")
    event_type: str
    source_service: str
    human_summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: EventSeverity = "info"
    status: EventStatus = "received"
    visibility: EventVisibility = "timeline"
    copy_policy: EventCopyPolicy = "copy_sanitized_only"
    speaker_allowed: bool = True
    correlation_id: str | None = None
    source_event_id: str | None = None
    raw_ref: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class PublicEventPayload(AIpinhoModel):
    event_id: str
    event_type: str
    source_service: str
    human_summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    severity: EventSeverity
    status: EventStatus
    visibility: EventVisibility
    copy_policy: EventCopyPolicy
    speaker_allowed: bool
    correlation_id: str | None = None
    source_event_id: str | None = None
    raw_available: bool = False
    raw_ref: str | None = None
    created_at: str


class EventCopyResponse(AIpinhoModel):
    event_id: str
    text: str
    copy_policy: EventCopyPolicy


class EventAuditRecord(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex}")
    action: str
    event_id: str | None = None
    event_type: str | None = None
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
