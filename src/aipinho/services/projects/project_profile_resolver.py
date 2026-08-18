from __future__ import annotations

from aipinho.schemas.projects import ProjectProfile
from aipinho.services.projects.project_profile_registry_service import ProjectProfileRegistryService


class ProjectProfileResolver:
    def __init__(self, registry: ProjectProfileRegistryService | None = None) -> None:
        self.registry = registry or ProjectProfileRegistryService()

    def resolve(self, *, project_id: str | None = None, path_ref: str | None = None) -> ProjectProfile | None:
        if project_id:
            try:
                return self.registry.get(project_id)
            except KeyError:
                return None
        if path_ref:
            return self.registry.resolve_by_path(path_ref)
        return None

    def context_summary(self, profile: ProjectProfile | None) -> dict[str, object]:
        if profile is None:
            return {"project_profile_id": None, "status": "not_resolved"}
        return {
            "project_profile_id": profile.project_id,
            "display_name": profile.display_name,
            "stack": profile.stack,
            "profile_status": profile.profile_status,
            "source_readonly_workspace_id": profile.source_readonly_workspace_id,
            "target_mutable_workspace_id": profile.target_mutable_workspace_id,
            "validation_profile_id": profile.validation_profile_id,
            "memory_namespace": profile.memory_namespace,
            "artifact_namespace": profile.artifact_namespace,
            "report_namespace": profile.report_namespace,
            "known_risks": profile.known_risks,
            "accepted_decisions": profile.accepted_decisions,
            "evidence_refs": [f"project_profile:{profile.project_id}", *profile.evidence_refs],
        }


