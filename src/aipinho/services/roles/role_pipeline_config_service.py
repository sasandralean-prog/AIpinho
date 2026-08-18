from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_pipeline import RolePipeline, RolePipelineConfig
from aipinho.utils.yaml_loader import load_yaml_file


class RolePipelineConfigService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_pipelines.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._pipelines: dict[str, RolePipeline] | None = None

    @property
    def pipelines(self) -> dict[str, RolePipeline]:
        if self._pipelines is None:
            parsed = RolePipelineConfig(**{"schema_version": self.config.get("schema_version", 1), "pipelines": {pid: {"pipeline_id": pid, **cfg} for pid, cfg in (self.config.get("pipelines", {}) or {}).items()}})
            self._pipelines = parsed.pipelines
        return self._pipelines

    def list_pipelines(self) -> dict[str, RolePipeline]:
        return dict(self.pipelines)

    def get_pipeline(self, pipeline_id: str) -> RolePipeline | None:
        return self.pipelines.get(pipeline_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_pipeline_config", "pipelines": len(self.pipelines)}
