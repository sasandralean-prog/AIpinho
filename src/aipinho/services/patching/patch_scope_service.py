from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.patch_scope import PatchScope
from aipinho.utils.yaml_loader import load_yaml_file


class PatchScopeService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "patch_scope_policy.yaml", critical=True, root=PATHS.config_root / "patching")

    def build(self, workspace: str, paths: list[str]) -> PatchScope:
        max_files = int((self.policy.get("scope", {}) or {}).get("max_files_per_plan", 5))
        unique = list(dict.fromkeys(paths))
        return PatchScope(workspace=workspace, affected_paths=unique[:max_files], omitted_paths=unique[max_files:], max_files=max_files)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_scope", "max_files_per_plan": int((self.policy.get("scope", {}) or {}).get("max_files_per_plan", 5))}
