from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from apps.launcher.ui.utils.formatting import as_text
from apps.launcher.ui.utils.redaction import redact


@dataclass(frozen=True)
class ArtifactPresentation:
    artifact_id: str | None
    filename: str
    content_type: str
    label: str
    size_bytes: int | None = None
    status: str = "ready"
    detail: str | None = None

    @property
    def actionable(self) -> bool:
        return bool(self.artifact_id and self.status == "ready")


@dataclass(frozen=True)
class ChatMessagePresentation:
    message_id: str | None
    role: str
    label: str
    text: str
    safety_label: str = "Seguro"
    task_id: str | None = None
    artifacts: list[ArtifactPresentation] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] | None = None

    def copy_text(self) -> str:
        parts = [f"{self.label}:"]
        if self.text:
            parts.append(self.text)
        if self.artifacts:
            parts.extend(artifact.label for artifact in self.artifacts if artifact.actionable)
        return "\n".join(parts).strip()


@dataclass(frozen=True)
class ChatPresentation:
    session_id: str | None
    messages: list[ChatMessagePresentation]
    state_lines: list[str]
    details: list[str]
    raw_payload: dict[str, Any]


class ChatPresentationMapper:
    ROLE_LABELS = {
        "user": "Voce",
        "assistant": "AIpinho",
        "speaker": "AIpinho",
        "system": "Sistema",
        "debugger": "Debugger",
    }
    TECHNICAL_NORMAL_KEYS = {
        "metadata",
        "endpoint_ref",
        "method",
        "side_effect",
        "raw_available",
        "raw_default_visible",
        "what_is_happening",
        "ref_id",
        "copy_policy",
    }

    def map(self, payload: dict[str, Any]) -> ChatPresentation:
        presentation = payload.get("presentation") if isinstance(payload.get("presentation"), dict) else None
        if presentation:
            return self._from_backend_presentation(payload, presentation)
        return self._from_timeline(payload)

    def normal_text(self, payload: dict[str, Any]) -> str:
        presentation = self.map(payload)
        lines: list[str] = []
        for message in presentation.messages:
            if not message.text and not message.artifacts:
                continue
            lines.append(f"{message.label}:")
            if message.text:
                lines.append(message.text)
            for artifact in message.artifacts:
                if artifact.actionable:
                    lines.append(artifact.label)
            lines.append("")
        if presentation.state_lines:
            lines.append("Estado")
            lines.extend(presentation.state_lines)
        return "\n".join(line for line in lines if line is not None).strip() or "Conversa carregada. Nenhuma mensagem para mostrar ainda."

    def _from_backend_presentation(self, root: dict[str, Any], presentation: dict[str, Any]) -> ChatPresentation:
        messages = [
            self._presentation_message(item)
            for item in self._list(presentation.get("messages"))
            if isinstance(item, dict)
        ]
        return ChatPresentation(
            session_id=self._string(root.get("session_id") or presentation.get("session_id")),
            messages=messages,
            state_lines=[self._string(item) for item in self._list(presentation.get("state_lines")) if self._string(item)],
            details=self._details_from_presentation(presentation),
            raw_payload=root,
        )

    def _from_timeline(self, payload: dict[str, Any]) -> ChatPresentation:
        timeline = payload.get("timeline") if isinstance(payload.get("timeline"), dict) else payload
        messages = [
            self._timeline_message(item)
            for item in self._list(timeline.get("messages"))
            if isinstance(item, dict)
        ]
        session_id = self._string(timeline.get("session_id") or payload.get("session_id"))
        latest = messages[-1] if messages else None
        state_lines = [
            f"Sessao: {session_id or 'sem sessao'}",
            f"Mensagens: {len(messages)}",
            f"Task: {latest.task_id if latest and latest.task_id else 'Sem task'}",
        ]
        return ChatPresentation(session_id=session_id, messages=messages, state_lines=state_lines, details=[], raw_payload=payload)

    def _presentation_message(self, item: dict[str, Any]) -> ChatMessagePresentation:
        role = self._string(item.get("role")) or "assistant"
        label = self._string(item.get("label")) or self.ROLE_LABELS.get(role, role)
        artifacts = self._artifacts_from_dicts(self._list(item.get("artifacts")))
        details = self._message_details(item, artifacts)
        return ChatMessagePresentation(
            message_id=self._string(item.get("message_id")),
            role=role,
            label=label,
            text=self._safe_text(item.get("text") or item.get("content")),
            safety_label=self._string(item.get("safety_label")) or "Seguro",
            task_id=self._string(item.get("task_id")),
            artifacts=artifacts,
            details=details,
            raw_payload=item,
        )

    def _timeline_message(self, item: dict[str, Any]) -> ChatMessagePresentation:
        role = self._string(item.get("role")) or "assistant"
        label = self.ROLE_LABELS.get(role, role)
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        artifacts = self._artifacts_from_message_metadata(metadata)
        details = self._message_details(item, artifacts)
        return ChatMessagePresentation(
            message_id=self._string(item.get("message_id")),
            role=role,
            label=label,
            text=self._safe_text(item.get("content") or item.get("text")),
            safety_label=self._safety(metadata),
            task_id=self._string(item.get("task_id")),
            artifacts=artifacts,
            details=details,
            raw_payload=item,
        )

    def _artifacts_from_message_metadata(self, metadata: dict[str, Any]) -> list[ArtifactPresentation]:
        raw_links = metadata.get("artifact_links_json")
        if isinstance(raw_links, str) and raw_links.strip():
            try:
                parsed = json.loads(raw_links)
            except json.JSONDecodeError:
                parsed = []
            if isinstance(parsed, list):
                return self._artifacts_from_dicts(parsed)
        artifact_id = self._string(metadata.get("artifact_id"))
        if not artifact_id:
            return []
        return self._artifacts_from_dicts([
            {
                "artifact_id": artifact_id,
                "filename": metadata.get("artifact_filename"),
                "content_type": metadata.get("artifact_content_type"),
                "label": metadata.get("artifact_label"),
                "size_bytes": metadata.get("artifact_size_bytes"),
            }
        ])

    def _artifacts_from_dicts(self, items: list[Any]) -> list[ArtifactPresentation]:
        artifacts: list[ArtifactPresentation] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            filename = self._string(item.get("filename")) or "artifact"
            artifact_id = self._string(item.get("artifact_id"))
            status = self._string(item.get("status")) or ("ready" if artifact_id else "degraded")
            label = self._string(item.get("label")) or f"Baixar {filename}"
            detail = None if artifact_id else "Artifact sem id acionavel. Nao e possivel baixar por este cliente."
            artifacts.append(
                ArtifactPresentation(
                    artifact_id=artifact_id,
                    filename=filename,
                    content_type=self._string(item.get("content_type")) or "application/octet-stream",
                    label=label,
                    size_bytes=self._optional_int(item.get("size_bytes")),
                    status=status,
                    detail=detail,
                )
            )
        return artifacts

    def _message_details(self, item: dict[str, Any], artifacts: list[ArtifactPresentation]) -> list[str]:
        details: list[str] = []
        for label, key in [
            ("message_id", "message_id"),
            ("task_id", "task_id"),
            ("trace_id", "trace_id"),
            ("status", "status"),
            ("safety", "safety_label"),
        ]:
            value = self._string(item.get(key))
            if value:
                details.append(f"{label}: {value}")
        for artifact in artifacts:
            if artifact.detail:
                details.append(artifact.detail)
            elif artifact.artifact_id:
                details.append(f"artifact_id: {artifact.artifact_id}")
        return details

    def _details_from_presentation(self, presentation: dict[str, Any]) -> list[str]:
        details: list[str] = []
        for item in self._list(presentation.get("details")):
            if isinstance(item, dict):
                label = self._string(item.get("label"))
                value = self._string(item.get("value"))
                if label and value:
                    details.append(f"{label}: {value}")
            elif self._string(item):
                details.append(self._string(item))
        return details

    def _safety(self, metadata: dict[str, Any]) -> str:
        for key in ("approval_required", "rag_used", "memory_used", "fallback_used"):
            if str(metadata.get(key, "")).lower() in {"true", "1", "yes", "sim"}:
                return "Atencao"
        return "Seguro"

    def _safe_text(self, value: Any) -> str:
        text = redact(self._string(value)).strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                for key in ("text", "response", "summary", "message", "content"):
                    candidate = self._string(parsed.get(key))
                    if candidate:
                        return redact(candidate)
                return "Mensagem tecnica disponivel nos detalhes."
        return text

    def _optional_int(self, value: Any) -> int | None:
        try:
            text = self._string(value)
            return int(text) if text else None
        except (TypeError, ValueError):
            return None

    def _list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _string(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return as_text(value)
        return str(value).strip()
