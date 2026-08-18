from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.hybrid_execution import DelegationLogSummary
from aipinho.services.events.event_core import redact_payload


class DelegationLogSummaryService:
    def summarize(
        self,
        *,
        status: str,
        events: list[Any],
        artifacts: list[dict[str, Any]],
        max_items: int = 5,
    ) -> DelegationLogSummary:
        limit = max(1, min(max_items, 20))
        errors: list[str] = []
        files: list[str] = []
        commands: list[str] = []
        next_steps: list[str] = []
        exit_code: int | None = None
        for event in events:
            payload = getattr(event, "payload_sanitized", {}) or {}
            severity = str(getattr(event, "severity", "info"))
            message = str(redact_payload(getattr(event, "human_message", "")))
            if severity in {"error", "critical"} and message and message not in errors:
                errors.append(message)
            for value in payload.get("files_changed", []) or payload.get("files_touched", []):
                if str(value) not in files:
                    files.append(str(redact_payload(value)))
            command = payload.get("command") or payload.get("normalized_command")
            if command and str(command) not in commands:
                commands.append(str(redact_payload(command)))
            if isinstance(payload.get("exit_code"), int):
                exit_code = payload["exit_code"]
            for item in payload.get("recommended_next_steps", []):
                if str(item) not in next_steps:
                    next_steps.append(str(redact_payload(item)))
        return DelegationLogSummary(
            status=status,
            top_errors=errors[:limit],
            files_touched=files[:limit],
            commands=commands[:limit],
            exit_code=exit_code,
            artifact_refs=[str(item.get("artifact_id")) for item in artifacts if item.get("artifact_id")][:limit],
            recommended_next_steps=next_steps[:limit],
            full_log_artifact_id=next((str(item.get("artifact_id")) for item in artifacts if item.get("metadata", {}).get("artifact_kind") == "full_log"), None),
        )

