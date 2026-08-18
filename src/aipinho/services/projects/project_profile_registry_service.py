from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.projects import (
    ProjectProfile,
    ProjectProfileCandidate,
    ProjectProfileCreateRequest,
    ProjectProfileSelectionRequest,
    ProjectProfileUpdateRequest,
    ProjectProfileValidationResult,
)
from aipinho.services.projects.project_profile_detector import ProjectProfileDetector
from aipinho.services.projects.project_profile_secret_scanner import ProjectProfileSecretScanner


class ProjectProfileRegistryService:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.environ.get("AIPINHO_PROJECT_PROFILES_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.config_root / "projects" / "profiles")
        self.backup_root = self.root / "backups"
        self.index_path = self.root / "PROJECT_PROFILES_INDEX.json"
        self.selection_path = self.root / "ACTIVE_PROJECT_SELECTIONS.json"
        self.detector = ProjectProfileDetector()
        self.scanner = ProjectProfileSecretScanner()
        self.root.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self._ensure_index()

    def status(self) -> dict[str, Any]:
        profiles = self.list_profiles()
        return {
            "status": "ok",
            "service": "project_profile_registry",
            "profile_count": len(profiles),
            "index_exists": self.index_path.exists(),
            "root": str(self.root),
        }

    def list_profiles(self) -> list[ProjectProfile]:
        rows = []
        for path in sorted(self.root.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            rows.append(self._load_profile(path))
        return rows

    def get(self, project_id: str) -> ProjectProfile:
        for profile in self.list_profiles():
            if profile.project_id == project_id:
                return profile
        raise KeyError(project_id)

    def detect(self, root_path: str, *, display_name: str | None = None, create_draft: bool = False) -> dict[str, Any]:
        candidate = self.detector.detect(root_path, display_name=display_name)
        proposed_profile = self.profile_from_candidate(candidate, display_name=display_name)
        response: dict[str, Any] = {
            "status": "ok",
            "candidate": candidate.model_dump(),
            "proposed_profile": proposed_profile.model_dump(),
        }
        if create_draft:
            saved = self.create(ProjectProfileCreateRequest(profile=proposed_profile, allow_needs_review=True))
            response["profile"] = saved.model_dump()
        return response

    def profile_from_candidate(self, candidate: ProjectProfileCandidate, *, display_name: str | None = None) -> ProjectProfile:
        slug = self._slug(display_name or Path(candidate.root_path).name)
        status = "draft" if candidate.confidence >= 0.5 else "needs_review"
        validation = candidate.suggested_validation_profile
        command_profiles = candidate.suggested_commands
        workspaces = candidate.suggested_workspaces
        return ProjectProfile(
            project_id=slug,
            display_name=display_name or Path(candidate.root_path).name or slug,
            slug=slug,
            profile_status=status,  # type: ignore[arg-type]
            root_ref=candidate.root_path,
            source_readonly_workspace_id=workspaces[0].workspace_id if workspaces else None,
            target_mutable_workspace_id=workspaces[1].workspace_id if len(workspaces) > 1 else None,
            stack=candidate.detected_stack,
            languages=self._languages(candidate.detected_stack),
            frameworks=self._frameworks(candidate.detected_stack),
            package_managers=self._package_managers(candidate.detected_files),
            build_system=self._build_system(candidate.detected_stack),
            test_system=self._test_system(candidate.detected_stack),
            validation_profile_id=validation.validation_profile_id if validation else None,
            command_profiles=command_profiles,
            workspace_profiles=workspaces,
            validation_profiles=[validation] if validation else [],
            memory_namespace=f"memory:project:{slug}",
            artifact_namespace=f"artifacts:projects:{slug}",
            report_namespace=f"reports:projects:{slug}",
            known_risks=candidate.risks,
            evidence_refs=candidate.evidence_refs,
            metadata_sanitized={"confidence": candidate.confidence, "missing_info": candidate.missing_info},
        )

    def create(self, request: ProjectProfileCreateRequest) -> ProjectProfile:
        profile = request.profile
        self._reject_secret(profile.model_dump())
        if profile.profile_status == "needs_review" and not request.allow_needs_review:
            raise ValueError("profile_needs_review")
        profile.updated_at = utc_now_iso()
        path = self._profile_path(profile.slug)
        if path.exists():
            self._backup(path)
        self._write_profile(path, profile)
        self._write_index()
        self._ensure_namespaces(profile)
        return profile

    def update(self, project_id: str, request: ProjectProfileUpdateRequest) -> ProjectProfile:
        profile = self.get(project_id)
        data = profile.model_dump()
        for key, value in request.model_dump(exclude_none=True).items():
            data[key] = value
        updated = ProjectProfile(**data)
        updated.updated_at = utc_now_iso()
        self._reject_secret(updated.model_dump())
        path = self._profile_path(updated.slug)
        self._backup(path)
        self._write_profile(path, updated)
        self._write_index()
        return updated

    def archive(self, project_id: str) -> ProjectProfile:
        profile = self.get(project_id)
        profile.profile_status = "archived"
        profile.updated_at = utc_now_iso()
        path = self._profile_path(profile.slug)
        self._backup(path)
        self._write_profile(path, profile)
        self._write_index()
        return profile

    def validate_profile(self, project_id: str) -> ProjectProfileValidationResult:
        profile = self.get(project_id)
        warnings: list[str] = []
        errors: list[str] = []
        if self.scanner.scan(profile.model_dump()):
            errors.append("profile_contains_secret_risk")
        for workspace in profile.workspace_profiles:
            if not Path(workspace.path).expanduser().exists():
                warnings.append(f"workspace_missing:{workspace.workspace_id}")
            if workspace.role == "source_readonly" and workspace.write_policy != "write_denied":
                errors.append(f"source_readonly_write_policy_invalid:{workspace.workspace_id}")
            if workspace.role == "target_mutable" and "governed" not in workspace.write_policy:
                warnings.append(f"target_mutable_write_policy_not_governed:{workspace.workspace_id}")
        if not profile.validation_profiles:
            warnings.append("validation_profile_missing")
        status = "invalid" if errors else ("needs_review" if warnings else "active")
        profile.profile_status = status  # type: ignore[assignment]
        profile.last_validated_at = utc_now_iso()
        profile.updated_at = utc_now_iso()
        self._write_profile(self._profile_path(profile.slug), profile)
        self._write_index()
        return ProjectProfileValidationResult(project_id=project_id, status=status, warnings=warnings, errors=errors, evidence_refs=[f"project_profile:{project_id}"])

    def select(self, request: ProjectProfileSelectionRequest) -> dict[str, Any]:
        profile = self.get(request.project_id)
        data = self._read_json(self.selection_path)
        key = request.session_id or request.agent_id or "global"
        data[key] = {
            "project_id": profile.project_id,
            "agent_id": request.agent_id,
            "session_id": request.session_id,
            "selected_at": utc_now_iso(),
            "evidence_refs": [f"project_profile:{profile.project_id}"],
        }
        self.selection_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "ok", "selection": data[key], "profile": profile.model_dump()}

    def resolve_by_path(self, path_ref: str) -> ProjectProfile | None:
        try:
            candidate = Path(path_ref).expanduser().resolve()
        except OSError:
            return None
        matches: list[tuple[int, ProjectProfile]] = []
        for profile in self.list_profiles():
            for workspace in profile.workspace_profiles:
                try:
                    root = Path(workspace.path).expanduser().resolve()
                    candidate.relative_to(root)
                except (ValueError, OSError):
                    continue
                matches.append((len(str(root)), profile))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def mobile_selector_view(self) -> dict[str, Any]:
        profiles = self.list_profiles()
        active = self._read_json(self.selection_path).get("global")
        return {
            "state": {
                "screen": "project_selector",
                "status": "ok",
                "raw_default_visible": False,
                "human_summary": "Selecione o projeto ativo antes de executar side effects.",
            },
            "active_project_id": active.get("project_id") if isinstance(active, dict) else None,
            "profiles": [
                {
                    "project_id": item.project_id,
                    "display_name": item.display_name,
                    "slug": item.slug,
                    "status": item.profile_status,
                    "stack": item.stack,
                    "root_ref": item.root_ref,
                    "source_readonly_workspace_id": item.source_readonly_workspace_id,
                    "target_mutable_workspace_id": item.target_mutable_workspace_id,
                    "validation_profile_id": item.validation_profile_id,
                    "warnings": ["profile_stale"] if item.profile_status == "stale" else [],
                }
                for item in profiles
            ],
        }

    def health(self, project_id: str) -> dict[str, Any]:
        profile = self.get(project_id)
        validation = self.validate_profile(project_id)
        return {"status": validation.status, "profile": profile.model_dump(), "validation": validation.model_dump()}

    def _reject_secret(self, payload: dict[str, Any]) -> None:
        if "secret_risk_detected" in payload.get("known_risks", []):
            raise ValueError("project_profile_secret_detected")
        findings = self.scanner.scan(payload)
        if findings:
            raise ValueError("project_profile_secret_detected")

    def _profile_path(self, slug: str) -> Path:
        return self.root / f"{self._slug(slug)}.yaml"

    def _load_profile(self, path: Path) -> ProjectProfile:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return ProjectProfile(**data)

    def _write_profile(self, path: Path, profile: ProjectProfile) -> None:
        text = yaml.safe_dump(profile.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
        path.write_text(text, encoding="utf-8")

    def _backup(self, path: Path) -> None:
        if path.exists():
            backup = self.backup_root / f"{path.stem}_{utc_now_iso().replace(':', '').replace('+', '_')}.yaml"
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    def _write_index(self) -> None:
        profiles = self.list_profiles()
        payload = {
            "schema_version": 1,
            "updated_at": utc_now_iso(),
            "profiles": [
                {
                    "project_id": item.project_id,
                    "slug": item.slug,
                    "display_name": item.display_name,
                    "profile_status": item.profile_status,
                    "stack": item.stack,
                    "root_ref": item.root_ref,
                    "last_validated_at": item.last_validated_at,
                    "evidence_refs": item.evidence_refs,
                }
                for item in profiles
            ],
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_index(self) -> None:
        if not self.index_path.exists():
            self._write_index()
        if not self.selection_path.exists():
            self.selection_path.write_text("{}", encoding="utf-8")

    def _ensure_namespaces(self, profile: ProjectProfile) -> None:
        (PATHS.project_root / "artifacts" / "projects" / profile.slug).mkdir(parents=True, exist_ok=True)
        (PATHS.reports_root / "projects" / profile.slug).mkdir(parents=True, exist_ok=True)

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
        return slug or "project"

    def _languages(self, stack: str) -> list[str]:
        if stack == "android_gradle":
            return ["kotlin", "java"]
        if stack == "python":
            return ["python"]
        if stack == "node":
            return ["javascript", "typescript"]
        if stack == "mixed":
            return ["mixed"]
        return []

    def _frameworks(self, stack: str) -> list[str]:
        return {"android_gradle": ["android"], "python": [], "node": [], "mixed": ["mixed"]}.get(stack, [])

    def _package_managers(self, files: list[str]) -> list[str]:
        managers = []
        if "gradlew.bat" in files or "gradlew" in files:
            managers.append("gradle_wrapper")
        if "package.json" in files:
            managers.append("npm")
        if "pyproject.toml" in files:
            managers.append("pyproject")
        if "requirements.txt" in files:
            managers.append("pip")
        return managers

    def _build_system(self, stack: str) -> str | None:
        return {"android_gradle": "gradle", "node": "npm", "python": "python"}.get(stack)

    def _test_system(self, stack: str) -> str | None:
        return {"android_gradle": "gradle_test", "node": "npm_test", "python": "pytest"}.get(stack)
