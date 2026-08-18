from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ArtifactAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("artifact", ["/api/v1/artifacts", "/api/v1/artifacts/zip"], "healthy", "Artifacts usam artifact_id, download e zip governado.")

