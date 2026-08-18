from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.templates import TemplateManifest, TemplateRegistryStatus
from aipinho.services.templates.template_validator import TemplateValidator
from aipinho.utils.yaml_loader import load_yaml_file


class TemplateRegistryService:
    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        registry_root: Path | None = None,
        validator: TemplateValidator | None = None,
    ) -> None:
        self.config = config or load_yaml_file(PATHS.config_root / "templates" / "template_registry.yaml", critical=False, root=PATHS.config_root)
        configured_root = self.config.get("registry_root") if isinstance(self.config, dict) else None
        self.registry_root = registry_root or (PATHS.project_root / str(configured_root) if configured_root else PATHS.config_root / "templates" / "registry")
        self.validator = validator or TemplateValidator()

    def list_templates(self, *, include_invalid: bool = False, include_disabled: bool = False) -> list[TemplateManifest]:
        templates: list[TemplateManifest] = []
        if not self.registry_root.exists():
            return []
        for path in sorted(self.registry_root.glob("*/template.yaml")):
            try:
                manifest = TemplateManifest(**load_yaml_file(path, critical=True, root=self.registry_root))
            except Exception:
                if include_invalid:
                    continue
                continue
            validation = self.validator.validate_manifest(manifest)
            if not include_invalid and not validation["valid"]:
                continue
            if not include_disabled and manifest.status in {"disabled", "invalid"}:
                continue
            templates.append(manifest)
        return templates

    def get(self, template_id: str) -> TemplateManifest | None:
        return next((item for item in self.list_templates(include_invalid=True, include_disabled=True) if item.template_id == template_id), None)

    def require(self, template_id: str) -> TemplateManifest:
        manifest = self.get(template_id)
        if manifest is None:
            raise FileNotFoundError(template_id)
        validation = self.validator.validate_manifest(manifest)
        if not validation["valid"] or manifest.status in {"disabled", "invalid"}:
            raise PermissionError("template_invalid_or_disabled")
        return manifest

    def find_by_project_type(self, project_type: str) -> TemplateManifest | None:
        matches = [item for item in self.list_templates() if project_type in item.supported_project_types]
        return matches[0] if matches else None

    def find(self, *, project_type: str = "unknown", language: str | None = None, platform: str | None = None, user_goal: str = "") -> TemplateManifest | None:
        if project_type != "unknown":
            match = self.find_by_project_type(project_type)
            if match is not None:
                return match
        goal = user_goal.casefold()
        candidates = self.list_templates()
        scored: list[tuple[int, TemplateManifest]] = []
        for manifest in candidates:
            score = 0
            if language and language in manifest.supported_languages:
                score += 3
            if platform and platform in manifest.supported_platforms:
                score += 3
            for example in manifest.examples:
                if any(token and token in goal for token in example.casefold().split()):
                    score += 1
            if score:
                scored.append((score, manifest))
        if scored:
            return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]
        return next((item for item in candidates if "generic_files" in item.supported_project_types), None)

    def health(self) -> TemplateRegistryStatus:
        raw = self.list_templates(include_invalid=True, include_disabled=True)
        valid = [item for item in raw if self.validator.validate_manifest(item)["valid"]]
        invalid = len(raw) - len(valid)
        return TemplateRegistryStatus(
            status="ok" if invalid == 0 and raw else "degraded" if raw else "empty",
            templates_loaded=len(raw),
            active_templates=sum(1 for item in valid if item.status == "active"),
            invalid_templates=invalid,
            version=str(self.config.get("version", 1) if isinstance(self.config, dict) else 1),
            warnings=[] if raw else ["template_registry_empty"],
        )
