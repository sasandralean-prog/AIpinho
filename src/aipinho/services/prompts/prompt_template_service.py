from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.prompts.prompt_template import PromptTemplate
from aipinho.utils.yaml_loader import load_yaml_file


class PromptTemplateService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "prompts" / "role_prompt_templates.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def get_template(self, role_id: str) -> PromptTemplate | None:
        roles = self.config.get("roles", {}) if isinstance(self.config.get("roles", {}), dict) else {}
        value = roles.get(role_id)
        if not isinstance(value, dict):
            return None
        return PromptTemplate(role_id=role_id, instruction=str(value.get("instruction", "")))

    def status(self) -> dict[str, object]:
        roles = self.config.get("roles", {}) if isinstance(self.config.get("roles", {}), dict) else {}
        return {"status": "ok", "service": "prompt_template", "roles": sorted(roles.keys())}
