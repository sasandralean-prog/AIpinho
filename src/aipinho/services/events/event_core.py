from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import (
    EventAuditRecord,
    EventContractDefinition,
    EventContractRegistryStatus,
    EventCopyResponse,
    EventPublishRequest,
    EventValidationResult,
    PublicEventPayload,
    StoredEvent,
)
from aipinho.utils.yaml_loader import load_yaml_file

_SECRET_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{12,}"),
)
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth_token",
    "credential",
    "credentials",
    "password",
    "refresh_token",
    "secret",
    "token",
    "access_token",
}


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _redact_text(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        return {str(k): redact_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_payload(v) for v in value]
    return value


def contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
    if isinstance(value, dict):
        return any(contains_secret(v) or (_is_sensitive_key(k) and bool(v)) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_secret(v) for v in value)
    return False


def _is_sensitive_key(key: Any) -> bool:
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", str(key).strip().casefold()).strip("_")
    return normalized in _SENSITIVE_KEYS


class EventContractRegistryService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "events" / "event_contract_registry.yaml"

    def _data(self) -> dict[str, Any]:
        return load_yaml_file(self.path, root=PATHS.project_root)

    def contracts(self) -> dict[str, EventContractDefinition]:
        raw = self._data().get("event_types", {})
        contracts: dict[str, EventContractDefinition] = {}
        for event_type, data in raw.items():
            contracts[event_type] = EventContractDefinition(
                event_type=event_type,
                required_fields=["event_type", "source_service", "human_summary"],
                allowed_sources=list(data.get("source_services", [])),
                default_visibility=str(data.get("visibility", "public")),
                default_severity=str(data.get("severity", "info")),
                default_status=str(data.get("default_status", "created")),
                copy_policy=str(data.get("copy_policy", "copy_sanitized")),
                speaker_allowed=bool(data.get("speaker_allowed", True)),
            )
        return contracts

    def get(self, event_type: str) -> EventContractDefinition | None:
        return self.contracts().get(event_type)

    def status(self) -> dict[str, object]:
        contracts = self.contracts()
        blocked = self._data().get("blocked", {})
        return EventContractRegistryStatus(
            status="ok" if contracts else "degraded",
            contracts_loaded=len(contracts),
            unknown_event_default="blocked" if blocked.get("unknown_event_type", True) else "allowed",
            missing_human_summary_default="blocked" if blocked.get("missing_human_summary", True) else "allowed",
        ).model_dump()


class EventContractValidator:
    def __init__(self, registry: EventContractRegistryService | None = None) -> None:
        self.registry = registry or EventContractRegistryService()

    def validate(self, request: EventPublishRequest) -> EventValidationResult:
        reasons: list[str] = []
        contract = self.registry.get(request.event_type)
        if contract is None:
            reasons.append("unknown_event_type")
            return EventValidationResult(allowed=False, event_type=request.event_type, reasons=reasons)
        if not request.source_service:
            reasons.append("missing_source_service")
        elif contract.allowed_sources and request.source_service not in contract.allowed_sources:
            reasons.append("source_service_not_allowed")
        if not request.human_summary or not request.human_summary.strip():
            reasons.append("missing_human_summary")
        if contains_secret(request.payload) or contains_secret(request.human_summary):
            reasons.append("secret_detected_in_public_event")
        if contains_secret(request.raw_payload):
            reasons.append("secret_detected_in_raw_payload")
        return EventValidationResult(
            allowed=not reasons,
            event_type=request.event_type,
            reasons=reasons,
            contract=contract,
        )


class EventRawPayloadStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_EVENT_RAW_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "interaction" / "raw")

    def store(self, event_id: str, raw_payload: dict[str, Any] | str | None) -> str | None:
        if raw_payload is None:
            return None
        self.root.mkdir(parents=True, exist_ok=True)
        raw_ref = f"raw_{event_id}"
        path = self.root / f"{raw_ref}.json"
        path.write_text(json.dumps({"raw_ref": raw_ref, "raw": raw_payload}, indent=2, ensure_ascii=True), encoding="utf-8")
        return raw_ref

    def read(self, raw_ref: str) -> dict[str, Any]:
        path = self.root / f"{raw_ref}.json"
        if not path.exists():
            raise FileNotFoundError(raw_ref)
        return json.loads(path.read_text(encoding="utf-8"))


class EventStoreRepository:
    def __init__(self, path: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_EVENT_STORE_ROOT")
        self.path = path or ((Path(env_root) / "events.jsonl") if env_root else PATHS.project_root / "data" / "runtime" / "events" / "store" / "events.jsonl")

    def append(self, event: StoredEvent) -> StoredEvent:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(event), ensure_ascii=True) + "\n")
        return event

    def list(self, limit: int = 100, since_cursor: str | None = None) -> list[StoredEvent]:
        if not self.path.exists():
            return []
        rows: list[StoredEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(StoredEvent(**json.loads(line)))
        start = 0
        if since_cursor and since_cursor.isdigit():
            start = min(int(since_cursor), len(rows))
        return rows[start:][-limit:]

    def cursor(self) -> str:
        if not self.path.exists():
            return "0"
        with self.path.open("r", encoding="utf-8") as handle:
            return str(sum(1 for line in handle if line.strip()))

    def get(self, event_id: str) -> StoredEvent | None:
        for event in self.list(limit=10000):
            if event.event_id == event_id:
                return event
        return None


class EventAuditService:
    def __init__(self, path: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_EVENT_AUDIT_ROOT")
        self.path = path or ((Path(env_root) / "event_audit.jsonl") if env_root else PATHS.project_root / "data" / "runtime" / "events" / "audit" / "event_audit.jsonl")

    def record(self, action: str, allowed: bool, reasons: list[str], event_id: str | None = None, event_type: str | None = None) -> EventAuditRecord:
        record = EventAuditRecord(action=action, event_id=event_id, event_type=event_type, allowed=allowed, reasons=reasons)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(record), ensure_ascii=True) + "\n")
        return record


class EventPublicPayloadBuilder:
    def build(self, event: StoredEvent) -> PublicEventPayload:
        return PublicEventPayload(
            event_id=event.event_id,
            event_type=event.event_type,
            source_service=event.source_service,
            human_summary=redact_payload(event.human_summary),
            payload=redact_payload(event.payload),
            severity=event.severity,
            status=event.status,
            visibility=event.visibility,
            copy_policy=event.copy_policy,
            speaker_allowed=event.speaker_allowed,
            correlation_id=event.correlation_id,
            source_event_id=event.source_event_id,
            raw_available=bool(event.raw_ref),
            raw_ref=event.raw_ref,
            created_at=event.created_at,
        )


class EventPublisherService:
    def __init__(self) -> None:
        self.registry = EventContractRegistryService()
        self.validator = EventContractValidator(self.registry)
        self.store = EventStoreRepository()
        self.raw_store = EventRawPayloadStore()
        self.audit = EventAuditService()

    def publish(self, request: EventPublishRequest) -> StoredEvent:
        validation = self.validator.validate(request)
        if not validation.allowed:
            self.audit.record("publish_blocked", False, validation.reasons, event_type=request.event_type)
            raise ValueError(",".join(validation.reasons))
        contract = validation.contract
        assert contract is not None
        event = StoredEvent(
            event_type=request.event_type,
            source_service=request.source_service,
            human_summary=redact_payload(request.human_summary),
            payload=redact_payload(request.payload),
            severity=request.severity or contract.default_severity,
            status=request.status or contract.default_status,
            visibility=request.visibility or contract.default_visibility,
            copy_policy=request.copy_policy or contract.copy_policy,
            speaker_allowed=contract.speaker_allowed,
            correlation_id=request.correlation_id,
            source_event_id=request.source_event_id,
        )
        raw_ref = self.raw_store.store(event.event_id, request.raw_payload)
        event.raw_ref = raw_ref
        self.store.append(event)
        self.audit.record("publish", True, [], event_id=event.event_id, event_type=event.event_type)
        return event


class EventCopyPolicyService:
    def copy(self, event_id: str) -> EventCopyResponse:
        event = EventStoreRepository().get(event_id)
        if event is None:
            raise FileNotFoundError(event_id)
        if event.copy_policy in {"copy_blocked", "blocked"}:
            raise PermissionError("copy_blocked")
        text = f"[{event.severity}] {event.event_type}: {event.human_summary}"
        return EventCopyResponse(event_id=event.event_id, text=text, copy_policy=event.copy_policy)


class EventTraceService:
    def trace(self, event_id: str) -> dict[str, object]:
        event = EventStoreRepository().get(event_id)
        if event is None:
            raise FileNotFoundError(event_id)
        return {"status": "ok", "event": EventPublicPayloadBuilder().build(event).model_dump(), "raw_hidden_by_default": True}


class EventStatusService:
    def status(self) -> dict[str, object]:
        registry = EventContractRegistryService().status()
        return {"status": registry.get("status", "degraded"), "event_store_cursor": EventStoreRepository().cursor(), **registry}
