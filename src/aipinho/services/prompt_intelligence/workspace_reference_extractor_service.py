from __future__ import annotations

import unicodedata
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.intent.workspace_reference import WorkspaceReference
from aipinho.services.prompt_intelligence.path_extraction_service import (
    PathExtractionService,
)
from aipinho.utils.yaml_loader import load_yaml_file


class WorkspaceReferenceExtractorService:
    def __init__(
        self,
        path_extractor: PathExtractionService | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.path_extractor = path_extractor or PathExtractionService()
        self.config = config or load_yaml_file(
            PATHS.config_root / "workspaces" / "workspace_reference_policy.yaml",
            critical=True,
            root=PATHS.config_root / "workspaces",
        )

    def extract(self, prompt: str) -> list[WorkspaceReference]:
        references: list[WorkspaceReference] = []
        window_chars = int(self.config.get("context_window_chars", 160) or 160)
        role_aliases = self.config.get("roles", {})
        for extracted in self.path_extractor.extract(prompt):
            start = max(0, extracted.start - window_chars)
            context = self._normalize(prompt[start:extracted.start])
            if self._excluded_by_context(context):
                continue
            role = "unknown"
            evidence = None
            confidence = 0.5
            if isinstance(role_aliases, dict):
                nearest: tuple[int, str, str] | None = None
                for role_id, raw in role_aliases.items():
                    aliases = raw.get("aliases", []) if isinstance(raw, dict) else []
                    for alias in aliases:
                        alias_text = self._normalize(str(alias))
                        position = context.rfind(alias_text)
                        if position < 0:
                            continue
                        if nearest is None or position > nearest[0]:
                            nearest = (position, str(role_id), str(alias))
                if nearest is not None:
                    _position, role, evidence = nearest
                    confidence = 0.95
            references.append(
                WorkspaceReference(
                    path=extracted.value,
                    role=role,
                    evidence=evidence,
                    confidence=confidence,
                )
            )
        return references

    def _excluded_by_context(self, context: str) -> bool:
        window_chars = int(
            self.config.get("exclusion_context_window_chars", 64)
            or 64
        )
        raw_aliases = self.config.get("exclude_context_suffixes", [])
        aliases = (
            raw_aliases
            if isinstance(raw_aliases, list)
            else []
        )
        tail = str(context or "")[-window_chars:].rstrip(
            " \t:;,-—–"
        )
        return any(
            tail.endswith(self._normalize(str(alias)))
            for alias in aliases
            if str(alias).strip()
        )

    def _normalize(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
