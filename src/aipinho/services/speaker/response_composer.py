from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class ResponseComposer:
    def product_state(self) -> dict[str, Any]:
        product = load_yaml_file(PATHS.config_root / "app" / "product.yaml", critical=False, root=PATHS.config_root / "app")
        identity = load_yaml_file(PATHS.config_root / "app" / "identity.yaml", critical=False, root=PATHS.config_root / "app")
        return {"identity": identity, "product": product}

    def bullet_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    def source_status(self) -> tuple[list[str], list[str]]:
        sources_config = load_yaml_file(PATHS.config_root / "policies" / "self_knowledge_sources.yaml", critical=False, root=PATHS.config_root / "policies")
        ok: list[str] = []
        missing: list[str] = []
        for source in sources_config.get("sources", []) or []:
            if not isinstance(source, dict):
                continue
            relative = str(source.get("path", ""))
            path = PATHS.project_root / relative
            if path.exists() and path.stat().st_size > 0:
                ok.append(relative)
            elif source.get("required", False):
                missing.append(relative)
        return ok, missing