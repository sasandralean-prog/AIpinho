from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ConceptMatch:
    concept_id: str
    concept_type: str
    alias: str
    normalized_alias: str
    confidence: float


class ConceptMatcher:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "concept_registry.yaml"
        self._config: dict[str, object] | None = None

    def load(self) -> "ConceptMatcher":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, object]:
        if self._config is None:
            self.load()
        return self._config or {}

    def normalize(self, text: str) -> str:
        matching = self.config.get("matching", {}) if isinstance(self.config.get("matching", {}), dict) else {}
        value = text.casefold() if matching.get("casefold", True) else text
        if matching.get("normalize_accents", True):
            value = "".join(ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch))
        return " ".join(value.split())

    def _concepts(self) -> dict[str, dict[str, object]]:
        concepts = self.config.get("concepts", {})
        return concepts if isinstance(concepts, dict) else {}

    def match(self, text: str) -> list[ConceptMatch]:
        normalized_text = self.normalize(text)
        matches: list[ConceptMatch] = []
        for concept_id, raw in self._concepts().items():
            if not isinstance(raw, dict):
                continue
            concept_type = str(raw.get("type", "unknown"))
            aliases = raw.get("aliases", [])
            if not isinstance(aliases, list):
                continue
            for alias in aliases:
                alias_text = str(alias)
                normalized_alias = self.normalize(alias_text)
                if normalized_alias and self._contains_alias(normalized_text, normalized_alias):
                    matches.append(ConceptMatch(concept_id, concept_type, alias_text, normalized_alias, 1.0))
                    break
        return matches

    def _contains_alias(self, normalized_text: str, normalized_alias: str) -> bool:
        pattern = re.escape(normalized_alias)
        if normalized_alias[0].isalnum() or normalized_alias[0] == "_":
            pattern = rf"(?<!\w){pattern}"
        if normalized_alias[-1].isalnum() or normalized_alias[-1] == "_":
            pattern = rf"{pattern}(?!\w)"
        return re.search(pattern, normalized_text, flags=re.UNICODE) is not None

    def has_type(self, matches: list[ConceptMatch], concept_type: str) -> bool:
        return any(match.concept_type == concept_type for match in matches)

    def by_type(self, matches: list[ConceptMatch], concept_type: str) -> list[ConceptMatch]:
        return [match for match in matches if match.concept_type == concept_type]

    def status(self) -> dict[str, object]:
        try:
            return {"status": "ok", "concepts": len(self._concepts())}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}
