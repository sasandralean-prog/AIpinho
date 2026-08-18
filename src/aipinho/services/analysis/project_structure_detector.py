from __future__ import annotations

from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.analysis.project_profile_service import ProjectProfileService


class ProjectStructureDetector:
    def __init__(self, profiles: ProjectProfileService | None = None) -> None:
        self.profiles = profiles or ProjectProfileService()

    def detect(self, tree: ProjectTreeSummary) -> list[str]:
        paths = set(tree.top_level) | set(tree.important_paths) | set(tree.candidate_files)
        normalized_paths = {path.replace("\\", "/") for path in paths}
        structures: list[str] = []
        if "pyproject.toml" in paths or "requirements.txt" in paths:
            structures.append("python_project")
        if "src" in tree.top_level or any(path.startswith("src/") for path in normalized_paths):
            structures.append("package_src_layout")
        if "tests" in tree.top_level or any(path.startswith("tests/") for path in normalized_paths):
            structures.append("tests_present")
        if "config" in tree.top_level or any(path.startswith("config/") for path in normalized_paths):
            structures.append("config_first_layout")
        if "docs" in tree.top_level or any(path.startswith("docs/") for path in normalized_paths):
            structures.append("docs_present")
        if any("api/routers" in path for path in normalized_paths):
            structures.append("api_routes_present")
        if any("services/" in path for path in normalized_paths):
            structures.append("services_present")
        if any("schemas/" in path for path in normalized_paths):
            structures.append("schemas_present")
        if any(path.endswith("app_factory.py") for path in normalized_paths):
            structures.append("fastapi_project")
        structures.extend(f"project_profile:{profile_id}" for profile_id in self.profiles.detect(tree))
        return list(dict.fromkeys(structures))

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "project_structure_detector",
            "profile_service": self.profiles.status(),
        }
