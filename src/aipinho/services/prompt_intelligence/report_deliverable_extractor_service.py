from __future__ import annotations

import re
import unicodedata
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class ReportDeliverableExtractorService:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "reports" / "report_deliverable_policy.yaml",
            critical=True,
            root=PATHS.config_root / "reports",
        )

    def extract(self, prompt: str) -> list[str]:
        normalized = self._normalize(prompt)
        candidates = [normalized]
        bullet_pattern = r"(?m)^\s*(?:[-*]|\u2022|\d+[.)])\s+(.+?)\s*$"
        candidates.extend(
            self._normalize(match.group(1))
            for match in re.finditer(bullet_pattern, prompt)
        )
        deliverables: list[str] = []
        definitions = self.config.get("deliverables", {})
        if not isinstance(definitions, dict):
            return deliverables
        for deliverable_id, raw in definitions.items():
            definition = raw if isinstance(raw, dict) else {}
            aliases = [
                self._normalize(str(alias))
                for alias in definition.get("aliases", [])
                if str(alias).strip()
            ]
            if any(
                self._contains_alias(candidate, alias)
                for candidate in candidates
                for alias in aliases
            ):
                deliverables.append(str(deliverable_id))
        return list(dict.fromkeys(deliverables))

    def definitions(self) -> dict[str, dict[str, Any]]:
        raw = self.config.get("deliverables", {})
        if not isinstance(raw, dict):
            return {}
        return {
            str(key): value if isinstance(value, dict) else {}
            for key, value in raw.items()
        }

    def _normalize(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", ascii_text).strip()

    def _contains_alias(self, text: str, alias: str) -> bool:
        if not alias:
            return False
        return re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text) is not None
