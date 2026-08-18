from __future__ import annotations

from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.services.roles.role_pipeline_config_service import RolePipelineConfigService


class RolePipelinePlanner:
    def __init__(self, config_service: RolePipelineConfigService | None = None) -> None:
        self.config_service = config_service or RolePipelineConfigService()

    def choose_pipeline(self, request: RolePipelineRunRequest) -> str:
        if request.pipeline_id:
            return request.pipeline_id
        intent = str(request.intent_map.get("intent_type", "conversation")) if isinstance(request.intent_map, dict) else "conversation"
        for pipeline in self.config_service.list_pipelines().values():
            if pipeline.enabled and intent in pipeline.allowed_intents:
                return pipeline.pipeline_id
        return "chat_basic"

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_pipeline_planner"}
