from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.projects.project_profile_registry_service import ProjectProfileRegistryService


class ProjectProfileHealthService:
    def __init__(self, registry: ProjectProfileRegistryService | None = None) -> None:
        self.registry = registry or ProjectProfileRegistryService()

    def status(self) -> dict[str, Any]:
        profiles = self.registry.list_profiles()
        warnings: list[str] = []
        errors: list[str] = []
        for profile in profiles:
            result = self.registry.validate_profile(profile.project_id)
            warnings.extend([f"{profile.project_id}:{item}" for item in result.warnings])
            errors.extend([f"{profile.project_id}:{item}" for item in result.errors])
        return {
            "status": "invalid" if errors else ("degraded" if warnings else "ok"),
            "profile_count": len(profiles),
            "index_exists": (PATHS.config_root / "projects" / "profiles" / "PROJECT_PROFILES_INDEX.json").exists(),
            "warnings": warnings,
            "errors": errors,
        }

    def write_report(self) -> tuple[Path, Path]:
        import json
        from datetime import datetime

        payload = self.status()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = PATHS.reports_root / "health"
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / f"project_profiles_health_{stamp}.json"
        md_path = out / f"project_profiles_health_{stamp}.md"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(
            "\n".join(
                [
                    f"# Project Profiles Health {stamp}",
                    "",
                    f"Status: {payload['status']}",
                    f"Profiles: {payload['profile_count']}",
                    "",
                    "## Warnings",
                    *[f"- {item}" for item in payload["warnings"]],
                    "",
                    "## Errors",
                    *[f"- {item}" for item in payload["errors"]],
                ]
            ),
            encoding="utf-8",
        )
        return md_path, json_path


