from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import yaml

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_lifecycle import ArtifactFormat
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactFormatValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_format_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")

    def detect_format(self, target_path: str) -> ArtifactFormat:
        suffix = Path(target_path).suffix.lower()
        if suffix == ".md":
            return "markdown"
        if suffix == ".txt":
            return "text"
        if suffix == ".json":
            return "json"
        if suffix in {".yaml", ".yml"}:
            return "yaml"
        if suffix == ".csv":
            return "csv"
        if suffix == ".html":
            return "html"
        return "unknown"

    def validate(self, content: str, fmt: str) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        if fmt == "json":
            try:
                json.loads(content)
            except Exception:
                return False, ["invalid_json"]
        elif fmt == "yaml":
            try:
                yaml.safe_load(content)
            except Exception:
                return False, ["invalid_yaml"]
        elif fmt == "html":
            lowered = content.lower()
            if "<script" in lowered:
                return False, ["html_script_tag_blocked"]
            if re.search(r"""(?i)(src|href)\s*=\s*["']https?://""", content):
                return False, ["html_external_resource_blocked"]
        elif fmt == "csv":
            try:
                list(csv.reader(io.StringIO(content)))
            except Exception:
                warnings.append("csv_parse_warning")
        elif fmt in {"markdown", "text"}:
            if not content.strip():
                return False, ["empty_content"]
        else:
            return False, ["unknown_format"]
        return True, warnings

    def pretty_preview(self, content: str, fmt: str) -> str:
        if fmt == "json":
            try:
                return json.dumps(json.loads(content), ensure_ascii=False, indent=2)
            except Exception:
                return content
        return content

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_format_validator"}
