from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ExtractedPath:
    value: str
    raw_value: str
    start: int
    end: int
    path_kind: str


class PathExtractionService:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "workspaces" / "workspace_resolution_policy.yaml",
            critical=True,
            root=PATHS.config_root / "workspaces",
        )

    @property
    def settings(self) -> dict[str, Any]:
        extraction = self.config.get("path_extraction", {})
        return extraction if isinstance(extraction, dict) else {}

    def extract(self, prompt: str) -> list[ExtractedPath]:
        windows = self.settings.get("windows_drive", {})
        if not isinstance(windows, dict):
            return []
        results: list[ExtractedPath] = []
        occupied: list[tuple[int, int]] = []
        for key in ("quoted_regex", "bare_regex"):
            pattern = str(windows.get(key, "")).strip()
            if not pattern:
                continue
            for match in re.finditer(pattern, prompt):
                group_index = 1 if match.lastindex else 0
                start, end = match.span(group_index)
                if any(start < used_end and end > used_start for used_start, used_end in occupied):
                    continue
                raw = match.group(group_index)
                value = self._normalize_windows_path(raw, windows)
                if not value:
                    continue
                consumed = max(1, min(len(raw), len(value)))
                end = start + consumed
                results.append(
                    ExtractedPath(
                        value=value,
                        raw_value=raw,
                        start=start,
                        end=end,
                        path_kind="windows_drive",
                    )
                )
                occupied.append((start, end))
        return sorted(results, key=lambda item: (item.start, item.end))

    def extract_first(self, prompt: str) -> ExtractedPath | None:
        paths = self.extract(prompt)
        return paths[0] if paths else None

    def _normalize_windows_path(self, raw: str, config: dict[str, Any]) -> str:
        trailing = str(config.get("strip_trailing", ".,;)"))
        value = raw.strip()
        if bool(config.get("split_before_next_drive", True)):
            value = re.split(r"\s+(?=[A-Za-z]:[\\/])", value, maxsplit=1)[0]
        stop_words = config.get("bare_stop_words")
        if not isinstance(stop_words, list):
            stop_words = []
        if stop_words:
            pattern = r"\s+(?:" + "|".join(re.escape(str(item)) for item in stop_words if item) + r")\b"
            value = re.split(pattern, value, maxsplit=1, flags=re.IGNORECASE)[0]
        value = value.rstrip(trailing)
        if not re.match(r"(?i)^[A-Z]:[\\/]", value):
            return ""
        normalized = str(PureWindowsPath(value))
        separator = str(config.get("normalize_separator", "\\"))
        if separator == "/":
            return normalized.replace("\\", "/")
        return normalized

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "path_extraction",
            "windows_drive_enabled": bool(self.settings.get("windows_drive")),
        }
