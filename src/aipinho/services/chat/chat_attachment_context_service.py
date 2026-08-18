from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aipinho.services.artifacts.artifact_interaction_core import ArtifactDownloadService, ArtifactRegistryRepository
from aipinho.services.events.event_core import contains_secret


@dataclass
class ChatAttachmentContext:
    artifact_ids: list[str] = field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    context_text: str = ""
    warnings: list[str] = field(default_factory=list)


class ChatAttachmentContextService:
    """Builds sanitized, bounded context from artifact ids attached to a chat message."""

    TEXT_PREFIXES = ("text/",)
    TEXT_CONTENT_TYPES = {
        "application/json",
        "application/xml",
        "application/yaml",
        "application/x-yaml",
    }

    def __init__(
        self,
        registry: ArtifactRegistryRepository | None = None,
        downloader: ArtifactDownloadService | None = None,
        max_artifacts: int = 8,
        max_chars_per_artifact: int = 12000,
    ) -> None:
        self.registry = registry or ArtifactRegistryRepository()
        self.downloader = downloader or ArtifactDownloadService()
        self.max_artifacts = max_artifacts
        self.max_chars_per_artifact = max_chars_per_artifact

    def from_metadata(self, metadata: dict[str, Any] | None) -> ChatAttachmentContext:
        raw_ids = (metadata or {}).get("attached_artifact_ids") or []
        artifact_ids = [str(item).strip() for item in raw_ids if str(item).strip()]
        unique_ids = list(dict.fromkeys(artifact_ids))[: self.max_artifacts]
        context = ChatAttachmentContext(artifact_ids=unique_ids)
        if len(artifact_ids) > len(unique_ids):
            context.warnings.append("attached_artifacts_limited")
        for artifact_id in unique_ids:
            record = self.registry.get(artifact_id)
            if record is None:
                context.warnings.append(f"attached_artifact_not_found:{artifact_id}")
                continue
            context.evidence_refs.append(
                {
                    "type": "artifact",
                    "ref_id": record.artifact_id,
                    "filename": record.filename,
                    "content_type": record.content_type,
                    "source": "chat_attachment",
                }
            )
            if not self._is_textual(record.content_type):
                context.warnings.append(f"attached_artifact_not_text:{record.artifact_id}")
                continue
            try:
                text = self.downloader.path(record.artifact_id).read_text(encoding="utf-8", errors="replace")
            except Exception:
                context.warnings.append(f"attached_artifact_unreadable:{record.artifact_id}")
                continue
            if contains_secret(text):
                context.warnings.append(f"attached_artifact_secret_risk:{record.artifact_id}")
                continue
            clipped = text[: self.max_chars_per_artifact]
            if len(text) > len(clipped):
                context.warnings.append(f"attached_artifact_truncated:{record.artifact_id}")
            context.context_text += f"\n\n[Anexo: {record.filename} | {record.artifact_id}]\n{clipped}"
        return context

    def _is_textual(self, content_type: str) -> bool:
        lowered = content_type.lower().split(";", 1)[0].strip()
        return lowered.startswith(self.TEXT_PREFIXES) or lowered in self.TEXT_CONTENT_TYPES
