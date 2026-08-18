from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.skills.contracts import (
    SkillHealth,
    SkillManifest,
    SkillManifestValidationResult,
    SkillRegistryStatusV2,
)
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.events.event_core import redact_payload
from aipinho.services.projects.project_profile_registry_service import ProjectProfileRegistryService
from aipinho.services.projects.project_profile_secret_scanner import ProjectProfileSecretScanner


SKILL_STATUS_ACTIVE = {"active", "experimental", "deprecated"}


class SkillManifestValidatorV2:
    REQUIRED_POLICIES = ("workspace_policy", "artifact_policy", "memory_policy", "validation_policy", "speaker_truth_policy")

    def __init__(self, tool_registry: AgentToolRegistryService | None = None) -> None:
        self.tool_registry = tool_registry or AgentToolRegistryService()
        self.secret_scanner = ProjectProfileSecretScanner()

    def validate(self, payload: SkillManifest | dict[str, Any]) -> SkillManifestValidationResult:
        reason_codes: list[str] = []
        warnings: list[str] = []
        manifest: SkillManifest | None = None
        try:
            manifest = payload if isinstance(payload, SkillManifest) else SkillManifest(**payload)
        except Exception as exc:
            return SkillManifestValidationResult(
                valid=False,
                status="invalid",
                reason_codes=["schema_invalid", str(type(exc).__name__)],
                safe_remediation=["Fix the manifest schema before enabling this skill."],
            )

        if self.secret_scanner.scan(manifest.model_dump()):
            reason_codes.append("secret_detected")
        if not self._valid_version(manifest.version):
            reason_codes.append("invalid_version")
        if not manifest.required_capabilities:
            reason_codes.append("missing_required_capabilities")
        if manifest.allowed_tools is None:
            reason_codes.append("missing_allowed_tools")
        if "*" in manifest.allowed_tools:
            reason_codes.append("unsafe_tool_allowed")
        if set(manifest.allowed_tools) & set(manifest.denied_tools):
            reason_codes.append("tool_cannot_be_allowed_and_denied")
        known_tools = {tool.tool_name for tool in self.tool_registry.list_tools()}
        unknown_tools = sorted(set(manifest.allowed_tools) - known_tools)
        reason_codes.extend([f"tool_not_registered:{item}" for item in unknown_tools])
        for policy_name in self.REQUIRED_POLICIES:
            if not getattr(manifest, policy_name):
                reason_codes.append(f"missing_{policy_name}")
        if manifest.workspace_policy.get("source_readonly_write") is True:
            reason_codes.append("source_readonly_write_declared")
        if "run_shell" in manifest.allowed_tools and manifest.risk_level not in {"high", "critical"}:
            warnings.append("shell_tool_requires_high_risk_review")
        if "patch_apply" in manifest.allowed_tools and manifest.approval_policy.get("required") is not True:
            reason_codes.append("side_effect_without_approval_policy")
        if manifest.status == "deprecated":
            warnings.append("deprecated_skill_warning")
        if manifest.status == "experimental" and not manifest.approval_policy.get("experimental_allowed", False):
            warnings.append("experimental_skill_requires_confirmation")
        valid = not reason_codes
        return SkillManifestValidationResult(
            skill_id=manifest.skill_id,
            valid=valid,
            status="accepted" if valid else "invalid",
            reason_codes=list(dict.fromkeys(reason_codes)),
            warnings=list(dict.fromkeys(warnings)),
            safe_remediation=self._remediation(reason_codes),
            manifest=manifest if valid else None,
        )

    def validate_for_project(self, manifest: SkillManifest, project_profile_id: str | None) -> SkillManifestValidationResult:
        base = self.validate(manifest)
        if not base.valid or not project_profile_id:
            return base
        try:
            profile = ProjectProfileRegistryService().get(project_profile_id)
        except KeyError:
            base.reason_codes.append("project_profile_not_found")
            base.valid = False
            base.status = "invalid"
            return base
        if profile.stack not in manifest.compatible_project_stacks and "mixed" not in manifest.compatible_project_stacks:
            base.reason_codes.append("incompatible_project_stack")
            base.valid = False
            base.status = "invalid"
        return base

    def _valid_version(self, value: str) -> bool:
        return bool(re.match(r"^\d+\.\d+\.\d+([+-][a-zA-Z0-9_.-]+)?$", value or ""))

    def _remediation(self, reasons: list[str]) -> list[str]:
        mapping = {
            "secret_detected": "Remove secret-like values and use environment variables or credential stores.",
            "source_readonly_write_declared": "Move writes to target_mutable or artifact/report workspaces.",
            "missing_validation_policy": "Declare validation_policy before enabling execution.",
            "missing_speaker_truth_policy": "Declare raw-hidden speaker truth policy.",
            "unsafe_tool_allowed": "Replace wildcard tools with an explicit allowlist.",
        }
        return [mapping.get(reason, f"Review manifest reason: {reason}") for reason in reasons]


class SkillManifestRegistryService:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.environ.get("AIPINHO_SKILL_REGISTRY_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.config_root / "skills" / "registry")
        self.backups_root = self.root / "backups"
        self.index_path = self.root / "skills_index.json"
        self.validator = SkillManifestValidatorV2()
        self.root.mkdir(parents=True, exist_ok=True)
        self.backups_root.mkdir(parents=True, exist_ok=True)
        self._ensure_seed_skills()
        self._write_index()

    def status(self) -> SkillRegistryStatusV2:
        manifests = self.list_manifests(include_archived=True)
        invalid = [manifest for manifest in manifests if not self.validator.validate(manifest).valid]
        return SkillRegistryStatusV2(
            status="ok" if manifests else "empty",
            manifest_count=len(manifests),
            active_count=len([item for item in manifests if item.status == "active"]),
            invalid_count=len(invalid),
            deprecated_count=len([item for item in manifests if item.status == "deprecated"]),
            experimental_count=len([item for item in manifests if item.status == "experimental"]),
            root=str(self.root),
        )

    def list_manifests(
        self,
        *,
        category: str | None = None,
        agent_id: str | None = None,
        project_stack: str | None = None,
        include_archived: bool = False,
    ) -> list[SkillManifest]:
        rows = [self._load_manifest(path) for path in self.root.glob("*/skill.yaml") if path.parent.name != "backups"]
        if not include_archived:
            rows = [item for item in rows if item.status != "archived"]
        if category:
            rows = [item for item in rows if item.category == category]
        if agent_id:
            rows = [item for item in rows if agent_id in item.compatible_agents]
        if project_stack:
            rows = [item for item in rows if project_stack in item.compatible_project_stacks or "mixed" in item.compatible_project_stacks]
        return sorted(rows, key=lambda item: item.skill_id)

    def get(self, skill_id: str) -> SkillManifest:
        for manifest in self.list_manifests(include_archived=True):
            if manifest.skill_id == skill_id:
                return manifest
        raise KeyError(skill_id)

    def save(self, manifest: SkillManifest) -> SkillManifest:
        validation = self.validator.validate(manifest)
        if not validation.valid:
            manifest = manifest.model_copy(update={"status": "invalid"})
        manifest = manifest.model_copy(update={"updated_at": utc_now_iso()})
        skill_dir = self.root / manifest.slug
        path = skill_dir / "skill.yaml"
        if path.exists():
            self._backup(path)
        skill_dir.mkdir(parents=True, exist_ok=True)
        yaml.safe_dump(manifest.model_dump(mode="json"), path.open("w", encoding="utf-8"), allow_unicode=True, sort_keys=False)
        (skill_dir / "skill.json").write_text(json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        if not (skill_dir / "README.md").exists():
            (skill_dir / "README.md").write_text(f"# {manifest.display_name}\n\n{manifest.description}\n", encoding="utf-8")
        if not (skill_dir / "tests.json").exists():
            (skill_dir / "tests.json").write_text(json.dumps({"tests": [], "generated": True}, indent=2), encoding="utf-8")
        self._write_index()
        return manifest

    def set_status(self, skill_id: str, status: str) -> SkillManifest:
        manifest = self.get(skill_id)
        updated = manifest.model_copy(update={"status": status, "updated_at": utc_now_iso()})
        return self.save(updated)

    def validate_manifest(self, skill_id_or_payload: str | dict[str, Any] | SkillManifest) -> SkillManifestValidationResult:
        if isinstance(skill_id_or_payload, str):
            return self.validator.validate(self.get(skill_id_or_payload))
        return self.validator.validate(skill_id_or_payload)

    def health(self) -> dict[str, Any]:
        rows: list[SkillHealth] = []
        for manifest in self.list_manifests(include_archived=True):
            validation = self.validator.validate(manifest)
            rows.append(SkillHealth(skill_id=manifest.skill_id, status=manifest.status, validation=validation, warnings=validation.warnings))
        return {"status": "ok", "skills": [row.model_dump() for row in rows], "registry": self.status().model_dump()}

    def categories(self) -> dict[str, Any]:
        categories = sorted({manifest.category for manifest in self.list_manifests(include_archived=True)})
        return {"status": "ok", "categories": categories}

    def mobile_view(self) -> dict[str, Any]:
        manifests = self.list_manifests(include_archived=False)
        return {
            "state": {"screen": "skills", "status": "ok", "raw_default_visible": False, "human_summary": "Skills internas governadas disponiveis."},
            "skills": [
                {
                    "skill_id": item.skill_id,
                    "display_name": item.display_name,
                    "version": item.version,
                    "status": item.status,
                    "category": item.category,
                    "risk_level": item.risk_level,
                    "capabilities": item.required_capabilities,
                    "enabled": item.status in SKILL_STATUS_ACTIVE,
                    "warnings": self.validator.validate(item).warnings,
                }
                for item in manifests
            ],
        }

    def _load_manifest(self, path: Path) -> SkillManifest:
        return SkillManifest(**(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))

    def _backup(self, path: Path) -> None:
        stamp = utc_now_iso().replace(":", "").replace("+", "_")
        target = self.backups_root / f"{path.parent.name}_{stamp}.yaml"
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    def _write_index(self) -> None:
        manifests = self.list_manifests(include_archived=True) if self.root.exists() else []
        payload = {
            "schema_version": 1,
            "updated_at": utc_now_iso(),
            "skills": [
                {
                    "skill_id": item.skill_id,
                    "slug": item.slug,
                    "display_name": item.display_name,
                    "version": item.version,
                    "status": item.status,
                    "category": item.category,
                    "risk_level": item.risk_level,
                    "compatible_agents": item.compatible_agents,
                }
                for item in manifests
            ],
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_seed_skills(self) -> None:
        if any(self.root.glob("*/skill.yaml")):
            return
        for manifest in _seed_manifests():
            self.save(manifest)


def _base_policy() -> dict[str, Any]:
    return {"source_readonly_write": False, "requires_project_profile_for_project_scoped": False}


def _artifact_policy() -> dict[str, Any]:
    return {"generate_report": True, "generate_markdown": True, "generate_zip": False, "requires_token": True, "expose_in_agent_artifact_panel": True}


def _validation_policy(required: bool = False) -> dict[str, Any]:
    return {"required": required, "failure_policy": "block_completion" if required else "allow_completed_with_warnings"}


def _seed_manifests() -> list[SkillManifest]:
    common_agents = ["aipinho", "codex", "lucio", "gemini"]
    return [
        SkillManifest(
            skill_id="internal.project_readonly_inventory",
            display_name="Project Read-only Inventory",
            slug="project_readonly_inventory",
            description="Analyze a project in read-only mode and generate an inventory report artifact.",
            version="1.0.0",
            status="active",
            category="analysis",
            compatible_agents=common_agents,
            compatible_project_stacks=["android_gradle", "python", "node", "mixed", "unknown"],
            required_capabilities=["read_workspace", "report_generate", "artifact_create", "use_project_profile"],
            allowed_tools=["list_dir", "generate_report"],
            denied_tools=["create_file", "modify_file", "patch_apply", "run_shell"],
            input_schema={"type": "object", "properties": {"workspace_id": {"type": "string"}, "max_depth": {"type": "integer"}}},
            output_schema={"type": "object", "required": ["summary", "artifact_id"], "properties": {"summary": {"type": "string"}, "artifact_id": {"type": "string"}}},
            side_effects=["artifact_create"],
            workspace_policy=_base_policy(),
            artifact_policy=_artifact_policy(),
            memory_policy={"mode": "propose_candidate", "requires_evidence": True},
            validation_policy=_validation_policy(False),
            speaker_truth_policy={"raw_hidden_by_default": True, "must_cite_evidence": True},
            risk_level="low",
            approval_policy={"required": False},
            docs_ref="docs/skills/INTERNAL_SKILLS_CATALOG.md",
            tests_ref="tests/skills",
        ),
        SkillManifest(
            skill_id="internal.safe_markdown_report_generator",
            display_name="Safe Markdown Report Generator",
            slug="safe_markdown_report_generator",
            description="Generate a sanitized markdown report artifact from supplied context and evidence references.",
            version="1.0.0",
            status="active",
            category="reporting",
            compatible_agents=common_agents,
            compatible_project_stacks=["android_gradle", "python", "node", "mixed", "unknown"],
            required_capabilities=["report_generate", "artifact_create"],
            allowed_tools=["generate_report"],
            denied_tools=["run_shell", "patch_apply"],
            input_schema={"type": "object", "properties": {"title": {"type": "string"}, "summary": {"type": "string"}}},
            output_schema={"type": "object", "required": ["summary", "artifact_id"], "properties": {"summary": {"type": "string"}, "artifact_id": {"type": "string"}}},
            side_effects=["artifact_create"],
            workspace_policy=_base_policy(),
            artifact_policy=_artifact_policy(),
            memory_policy={"mode": "none"},
            validation_policy=_validation_policy(False),
            speaker_truth_policy={"raw_hidden_by_default": True, "must_cite_evidence": True},
            risk_level="low",
            approval_policy={"required": False},
            docs_ref="docs/skills/INTERNAL_SKILLS_CATALOG.md",
            tests_ref="tests/skills",
        ),
        SkillManifest(
            skill_id="internal.validation_runner",
            display_name="Validation Runner",
            slug="validation_runner",
            description="Record or run governed validation for a project profile through Tool Gateway contracts.",
            version="1.0.0",
            status="active",
            category="validation",
            compatible_agents=["aipinho", "codex"],
            compatible_project_stacks=["android_gradle", "python", "node", "mixed", "unknown"],
            required_capabilities=["validation", "run_tests", "report_generate"],
            allowed_tools=["validate", "generate_report"],
            denied_tools=["patch_apply"],
            input_schema={"type": "object", "properties": {"status": {"type": "string"}, "name": {"type": "string"}}},
            output_schema={"type": "object", "required": ["summary", "validation_id"], "properties": {"summary": {"type": "string"}, "validation_id": {"type": "string"}}},
            side_effects=["validation_record", "artifact_create"],
            workspace_policy=_base_policy(),
            command_policy={"destructive_commands": "blocked", "unknown_shell": "blocked"},
            artifact_policy=_artifact_policy(),
            memory_policy={"mode": "propose_candidate", "requires_evidence": True},
            validation_policy=_validation_policy(True),
            speaker_truth_policy={"raw_hidden_by_default": True, "must_cite_validation": True},
            risk_level="medium",
            approval_policy={"required": False},
            docs_ref="docs/skills/INTERNAL_SKILLS_CATALOG.md",
            tests_ref="tests/skills",
        ),
        SkillManifest(
            skill_id="internal.mobile_ux_static_audit",
            display_name="Mobile UX Static Audit",
            slug="mobile_ux_static_audit",
            description="Inspect mobile UI files read-only and generate a UX audit artifact.",
            version="1.0.0",
            status="experimental",
            category="mobile_ux",
            compatible_agents=["aipinho", "codex", "lucio"],
            compatible_project_stacks=["android_gradle", "kotlin_android", "mixed", "unknown"],
            required_capabilities=["read_workspace", "report_generate", "artifact_create"],
            allowed_tools=["list_dir", "search_files", "generate_report"],
            denied_tools=["create_file", "modify_file", "patch_apply", "run_shell"],
            input_schema={"type": "object", "properties": {"workspace_id": {"type": "string"}, "query": {"type": "string"}}},
            output_schema={"type": "object", "required": ["summary", "artifact_id"], "properties": {"summary": {"type": "string"}, "artifact_id": {"type": "string"}}},
            side_effects=["artifact_create"],
            workspace_policy=_base_policy(),
            artifact_policy=_artifact_policy(),
            memory_policy={"mode": "none"},
            validation_policy=_validation_policy(False),
            speaker_truth_policy={"raw_hidden_by_default": True, "must_cite_evidence": True},
            risk_level="low",
            approval_policy={"required": False, "experimental_allowed": True},
            docs_ref="docs/skills/INTERNAL_SKILLS_CATALOG.md",
            tests_ref="tests/skills",
        ),
        SkillManifest(
            skill_id="internal.artifact_bundle_exporter",
            display_name="Artifact Bundle Exporter",
            slug="artifact_bundle_exporter",
            description="Create a governed bundle report for selected artifacts without exposing tokens in URLs.",
            version="1.0.0",
            status="active",
            category="artifact_generation",
            compatible_agents=common_agents,
            compatible_project_stacks=["android_gradle", "python", "node", "mixed", "unknown"],
            required_capabilities=["artifact_download", "artifact_create"],
            allowed_tools=["download_artifact", "create_artifact"],
            denied_tools=["run_shell", "patch_apply"],
            input_schema={"type": "object", "properties": {"artifact_ids": {"type": "array"}}},
            output_schema={"type": "object", "required": ["summary", "artifact_id"], "properties": {"summary": {"type": "string"}, "artifact_id": {"type": "string"}}},
            side_effects=["artifact_create"],
            workspace_policy=_base_policy(),
            artifact_policy={"generate_zip": True, "requires_token": True, "expose_in_agent_artifact_panel": True},
            memory_policy={"mode": "none"},
            validation_policy=_validation_policy(False),
            speaker_truth_policy={"raw_hidden_by_default": True, "must_cite_evidence": True},
            risk_level="low",
            approval_policy={"required": False},
            docs_ref="docs/skills/INTERNAL_SKILLS_CATALOG.md",
            tests_ref="tests/skills",
        ),
    ]
