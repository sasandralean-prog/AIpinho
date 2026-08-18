from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class TaskPipelineAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("task_pipeline", ["/api/v1/tasks/cards", "/api/v1/task-runs", "/api/v1/pipeline/cards/{task_id}"], "unknown", "Pipeline agrega task state, gates e next safe action.")

