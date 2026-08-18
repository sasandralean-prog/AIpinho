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
            role = "unknown"
            evidence = None
            confidence = 0.5
            if isinstance(role_aliases, dict):
                for role_id, raw in role_aliases.items():
                    aliases = raw.get("aliases", []) if isinstance(raw, dict) else []
                    matched = next(
                        (
                            str(alias)
                            for alias in aliases
                            if self._normalize(str(alias)) in context
                        ),
                        None,
                    )
                    if matched:
                        role = str(role_id)
                        evidence = matched
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

    def _normalize(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
