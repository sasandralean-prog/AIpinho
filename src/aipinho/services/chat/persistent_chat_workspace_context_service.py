from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService


class PersistentChatWorkspaceContextService:
    """Resolves active workspace context from persisted chat messages."""

    STRUCTURED_METADATA_KEYS = (
        "workspace_context",
        "workspace_path",
        "workspace_ref",
        "active_workspace",
        "target_workspace",
    )

    def __init__(self, path_extractor: PathExtractionService | None = None) -> None:
        self.path_extractor = path_extractor or PathExtractionService()

    def from_messages(self, messages: list[Any]) -> str | None:
        for message in reversed(messages):
            metadata = getattr(message, "metadata", {}) or {}
            for key in self.STRUCTURED_METADATA_KEYS:
                candidate = self._from_candidate(metadata.get(key))
                if candidate:
                    return candidate
        for message in reversed(messages):
            if getattr(message, "role", None) != "user":
                continue
            paths = self.path_extractor.extract(str(getattr(message, "content", "") or ""))
            if paths:
                return paths[0].value
        for message in reversed(messages):
            metadata = getattr(message, "metadata", {}) or {}
            candidate = self._from_candidate(metadata.get("file_path"))
            if candidate:
                return candidate
        return None

    def _from_candidate(self, value: object) -> str | None:
        if value is None:
            return None
        extracted = self.path_extractor.extract(str(value).strip())
        if not extracted:
            return None
        path = Path(extracted[0].value)
        if path.suffix:
            path = path.parent
        return str(path)
