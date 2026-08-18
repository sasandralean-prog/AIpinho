from __future__ import annotations

from typing import Any

from aipinho.schemas.maintenance.contracts import AnomalySignal
from aipinho.services.events.event_core import redact_payload


class StructuredSignalCollector:
    signal_type = "generic"

    def collect(self, snapshot: dict[str, Any] | None) -> list[AnomalySignal]:
        if not snapshot:
            return []
        payload = redact_payload(snapshot)
        return [
            AnomalySignal(
                signal_type=self.signal_type,
                source_ref=str(payload.get("source_ref", self.signal_type)),
                severity=str(payload.get("severity", "info")),
                summary=str(payload.get("summary", f"{self.signal_type} signal collected.")),
                details=payload,
            )
        ]


class EventSignalCollector(StructuredSignalCollector):
    signal_type = "event"


class DebuggerSignalCollector(StructuredSignalCollector):
    signal_type = "debugger"


class ContextSignalCollector(StructuredSignalCollector):
    signal_type = "context"


class SkillSignalCollector(StructuredSignalCollector):
    signal_type = "skill"


class PolicySignalCollector(StructuredSignalCollector):
    signal_type = "policy"


class RagSignalCollector(StructuredSignalCollector):
    signal_type = "rag"


class SpeakerSignalCollector(StructuredSignalCollector):
    signal_type = "speaker"


class ModelSignalCollector(StructuredSignalCollector):
    signal_type = "model"


class SupervisorSignalCollector(StructuredSignalCollector):
    signal_type = "supervisor"
