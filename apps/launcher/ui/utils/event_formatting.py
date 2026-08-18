from __future__ import annotations


def event_title(event: dict[str, object]) -> str:
    return f"[{event.get('severity','info')}] {event.get('event_type','unknown')} - {event.get('source_service','unknown')}"


def is_unknown_event(event: dict[str, object], known_contracts: set[str]) -> bool:
    return str(event.get("event_type")) not in known_contracts
