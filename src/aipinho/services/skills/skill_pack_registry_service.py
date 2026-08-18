from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.skills.skill_packs import (
    SkillPackExecutionRequest,
    SkillPackExecutionResult,
    SkillPackHealth,
    SkillPackManifest,
    SkillPackRegistryStatus,
    SkillPackSelectionCandidate,
    SkillPackSelectionRequest,
    SkillPackSelectionResult,
    SkillPackValidationResult,
)
from aipinho.schemas.skills.contracts import SkillExecutionRequest
from aipinho.services.events.event_core import redact_payload
from aipinho.services.projects.project_profile_secret_scanner import ProjectProfileSecretScanner
from aipinho.services.skills.skill_execution_service import SkillExecutionService
from aipinho.services.skills.skill_manifest_registry_service import (
    SKILL_STATUS_ACTIVE,
    SkillManifestRegistryService,
)
from aipinho.utils.yaml_loader import load_yaml_file


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
VALID_PACK_STATUSES = {"active", "experimental", "deprecated", "disabled", "invalid", "archived"}
VALID_AGENTS = {"aipinho", "lucio", "codex", "gemini", "autopilot"}


def _tokens(value: str | None) -> set[str]:
    tokens: set[str] = set()
    for raw in re.findall(r"[a-z0-9_]+", (value or "").casefold()):
        parts = [part for part in raw.split("_") if part]
        for token in [raw, *parts]:
            tokens.add(token)
            if token.endswith("ies") and len(token) > 4:
                tokens.add(f"{token[:-3]}y")
            for suffix in ("ing", "ed", "es", "s"):
                if token.endswith(suffix) and len(token) > len(suffix) + 3:
                    tokens.add(token[: -len(suffix)])
    return tokens


def _search_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return " ".join(_search_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_search_text(item) for item in value.values())
    if hasattr(value, "model_dump"):
        return _search_text(value.model_dump())
    return str(value)


class SkillPackValidator:
    def __init__(self, skill_registry: SkillManifestRegistryService | None = None) -> None:
        self.skill_registry = skill_registry or SkillManifestRegistryService()
        self.secret_scanner = ProjectProfileSecretScanner()

    def validate(self, payload: SkillPackManifest | dict[str, Any]) -> SkillPackValidationResult:
        reason_codes: list[str] = []
        warnings: list[str] = []
        manifest: SkillPackManifest | None = None
        try:
            manifest = payload if isinstance(payload, SkillPackManifest) else SkillPackManifest(**payload)
        except Exception as exc:
            return SkillPackValidationResult(
                valid=False,
                status="invalid",
                reason_codes=["schema_invalid", str(type(exc).__name__)],
                safe_remediation=["Fix the pack manifest schema before enabling this pack."],
                health_status="invalid",
            )

        if self.secret_scanner.scan(manifest.model_dump()):
            reason_codes.append("secret_detected")
        if not self._valid_version(manifest.version):
            reason_codes.append("invalid_pack_version")
        if manifest.status not in VALID_PACK_STATUSES:
            reason_codes.append("invalid_pack_status")
        if len(set(manifest.included_skills)) != len(manifest.included_skills):
            reason_codes.append("duplicate_included_skill")
        for agent in manifest.supported_agents:
            if agent not in VALID_AGENTS:
                reason_codes.append(f"invalid_supported_agent:{agent}")
        for ref_name, ref_value in {"docs_ref": manifest.docs_ref, "tests_ref": manifest.tests_ref}.items():
            if not self._ref_exists(ref_value):
                reason_codes.append(f"missing_{ref_name}")
        if not manifest.policy_profile:
            reason_codes.append("policy_profile_missing")
        if not manifest.artifact_policy:
            reason_codes.append("artifact_policy_missing")
        if manifest.risk_level in {"medium", "high", "critical"} and not manifest.validation_profile:
            warnings.append("validation_policy_missing")

        for skill_id in manifest.included_skills:
            try:
                skill = self.skill_registry.get(skill_id)
            except KeyError:
                reason_codes.append(f"missing_included_skill:{skill_id}")
                continue
            validation = self.skill_registry.validate_manifest(skill)
            if not validation.valid:
                reason_codes.append(f"invalid_skill_manifest:{skill_id}")
            if skill.workspace_policy.get("source_readonly_write") is True:
                reason_codes.append(f"source_readonly_write_declared:{skill_id}")
            if {"run_shell", "sandbox_run_shell"} & set(skill.allowed_tools) and not skill.command_policy:
                reason_codes.append(f"shell_policy_missing:{skill_id}")
            if skill.status == "deprecated":
                warnings.append(f"deprecated_skill:{skill_id}")
            if skill.status == "experimental":
                warnings.append(f"experimental_skill:{skill_id}")

        if manifest.status == "deprecated":
            warnings.append("deprecated_pack")
        if manifest.status == "experimental":
            warnings.append("experimental_pack")
            if not self._experimental_allowed():
                reason_codes.append("experimental_pack_not_enabled")
        if manifest.status in {"disabled", "archived"}:
            reason_codes.append(f"{manifest.status}_pack")

        valid = not reason_codes
        health = "ok" if valid and not warnings else "degraded" if valid else "invalid"
        return SkillPackValidationResult(
            skill_pack_id=manifest.skill_pack_id,
            valid=valid,
            status="accepted" if valid else "invalid",
            reason_codes=list(dict.fromkeys(reason_codes)),
            warnings=list(dict.fromkeys(warnings)),
            safe_remediation=self._remediation(reason_codes),
            manifest=manifest if valid else None,
            health_status=health,
        )

    def _experimental_allowed(self) -> bool:
        config = load_yaml_file(PATHS.config_root / "skills" / "skill_packs.yaml", critical=False, root=PATHS.config_root)
        experimental = config.get("experimental") if isinstance(config, dict) else {}
        return bool((experimental or {}).get("allow_experimental_packs", False))

    def _valid_version(self, value: str) -> bool:
        return bool(re.match(r"^\d+\.\d+\.\d+([+-][a-zA-Z0-9_.-]+)?$", value or ""))

    def _ref_exists(self, value: str) -> bool:
        path = (PATHS.project_root / value).resolve()
        try:
            path.relative_to(PATHS.project_root)
        except ValueError:
            return False
        return path.exists()

    def _remediation(self, reasons: list[str]) -> list[str]:
        mapping = {
            "secret_detected": "Remove secret-like values from the pack manifest.",
            "invalid_pack_version": "Use semantic versioning, for example 1.0.0.",
            "policy_profile_missing": "Declare an explicit policy_profile.",
            "artifact_policy_missing": "Declare an explicit artifact_policy.",
            "experimental_pack_not_enabled": "Enable experimental packs explicitly in config/skills/skill_packs.yaml.",
        }
        return [mapping.get(reason.split(":")[0], f"Review pack validation reason: {reason}") for reason in reasons]


class SkillPackRegistry:
    def __init__(self, root: Path | None = None, skill_registry: SkillManifestRegistryService | None = None) -> None:
        config = load_yaml_file(PATHS.config_root / "skills" / "skill_packs.yaml", critical=False, root=PATHS.config_root)
        configured_root = config.get("registry_root") if isinstance(config, dict) else None
        env_root = os.environ.get("AIPINHO_SKILL_PACKS_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / str(configured_root or "config/skills/packs"))
        self.skill_registry = skill_registry or SkillManifestRegistryService()
        self.validator = SkillPackValidator(self.skill_registry)
        self.index_path = self.root / "skill_packs_index.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self._write_index()

    def list_packs(
        self,
        *,
        category: str | None = None,
        agent_id: str | None = None,
        project_stack: str | None = None,
        include_archived: bool = False,
    ) -> list[SkillPackManifest]:
        rows = [self._load_manifest(path) for path in self.root.glob("*/pack.yaml")]
        if not include_archived:
            rows = [item for item in rows if item.status != "archived"]
        if category:
            rows = [item for item in rows if item.category == category]
        if agent_id:
            rows = [item for item in rows if agent_id in item.supported_agents]
        if project_stack:
            rows = [item for item in rows if project_stack in item.supported_project_stacks or "mixed" in item.supported_project_stacks]
        return sorted(rows, key=lambda item: item.skill_pack_id)

    def get(self, skill_pack_id: str) -> SkillPackManifest:
        for manifest in self.list_packs(include_archived=True):
            if manifest.skill_pack_id == skill_pack_id:
                return manifest
        raise KeyError(skill_pack_id)

    def validate_pack(self, skill_pack_id_or_payload: str | dict[str, Any] | SkillPackManifest) -> SkillPackValidationResult:
        if isinstance(skill_pack_id_or_payload, str):
            return self.validator.validate(self.get(skill_pack_id_or_payload))
        return self.validator.validate(skill_pack_id_or_payload)

    def status(self) -> SkillPackRegistryStatus:
        packs = self.list_packs(include_archived=True)
        validations = [self.validator.validate(pack) for pack in packs]
        return SkillPackRegistryStatus(
            status="ok" if packs and all(item.valid or item.skill_pack_id for item in validations) else "empty" if not packs else "degraded",
            pack_count=len(packs),
            active_count=len([item for item in packs if item.status == "active"]),
            invalid_count=len([item for item in validations if not item.valid]),
            deprecated_count=len([item for item in packs if item.status == "deprecated"]),
            experimental_count=len([item for item in packs if item.status == "experimental"]),
            root=str(self.root),
            skill_packs_enabled=self._enabled(),
        )

    def health(self) -> dict[str, Any]:
        packs = self.list_packs(include_archived=True)
        rows = [
            SkillPackHealth(
                skill_pack_id=pack.skill_pack_id,
                status=pack.status,
                health_status=(validation := self.validator.validate(pack)).health_status,
                validation=validation,
                skill_count=len(pack.included_skills),
                warnings=validation.warnings,
            ).model_dump()
            for pack in packs
        ]
        return {"status": "ok" if packs else "empty", "registry": self.status().model_dump(), "packs": rows}

    def select(self, request: SkillPackSelectionRequest) -> SkillPackSelectionResult:
        candidates: list[SkillPackSelectionCandidate] = []
        blocked: list[str] = []
        goal_tokens = _tokens(request.user_goal)
        requested_capabilities = set(request.requested_capabilities)
        for pack in self.list_packs(agent_id=request.agent_id, project_stack=request.project_stack):
            validation = self.validator.validate(pack)
            if not validation.valid:
                blocked.append(f"invalid_pack:{pack.skill_pack_id}")
                continue
            if RISK_ORDER.get(pack.risk_level, 99) > RISK_ORDER.get(request.risk_ceiling, 3):
                continue
            if request.execution_mode and request.execution_mode not in pack.supported_execution_modes:
                continue
            score = 0.0
            reasons: list[str] = []
            text = " ".join([
                pack.skill_pack_id,
                pack.display_name,
                pack.category,
                pack.description,
                _search_text(pack.examples),
                _search_text(pack.limitations),
                " ".join(pack.included_skills),
                " ".join(pack.required_capabilities),
                " ".join(pack.optional_capabilities),
                " ".join(pack.supported_project_stacks),
            ])
            overlap = goal_tokens & _tokens(text)
            if overlap:
                score += min(1.2, 0.18 * len(overlap))
                reasons.append("goal_evidence_match")
            if requested_capabilities & set(pack.required_capabilities + pack.optional_capabilities):
                score += 0.25
                reasons.append("capability_match")
            if request.execution_mode and request.execution_mode in pack.supported_execution_modes:
                score += 0.3
                reasons.append("execution_mode_match")
            if request.project_stack and (request.project_stack in pack.supported_project_stacks or "mixed" in pack.supported_project_stacks):
                score += 0.2
                reasons.append("project_stack_match")
            if score > 0:
                candidates.append(SkillPackSelectionCandidate(
                    skill_pack_id=pack.skill_pack_id,
                    score=round(score, 3),
                    reasons=reasons,
                    selected_skills=pack.included_skills,
                    risk_level=pack.risk_level,
                ))
        candidates.sort(key=lambda item: (-item.score, item.skill_pack_id))
        return SkillPackSelectionResult(
            status="selected" if candidates else "blocked",
            candidates=candidates,
            blocked_reasons=list(dict.fromkeys(blocked or ([] if candidates else ["no_eligible_skill_pack"]))),
            evidence_refs=["skill_pack_registry:selection"],
        )

    def mobile_view_model(self) -> dict[str, Any]:
        packs = self.list_packs(include_archived=False)
        return {
            "state": {
                "screen": "skill_packs",
                "status": "ok" if packs else "empty",
                "raw_default_visible": False,
                "human_summary": "Pacotes internos de capacidades governadas disponiveis.",
            },
            "packs": [
                {
                    "skill_pack_id": pack.skill_pack_id,
                    "display_name": pack.display_name,
                    "version": pack.version,
                    "status": pack.status,
                    "category": pack.category,
                    "risk_level": pack.risk_level,
                    "health": self.validator.validate(pack).health_status,
                    "skills": pack.included_skills,
                    "dashboard_visible": pack.dashboard_visible,
                    "supported_agents": pack.supported_agents,
                    "actions": [
                        {"label": "Detalhes", "endpoint": f"/api/v1/skill-packs/{pack.skill_pack_id}"},
                        {"label": "Abrir Debugger", "endpoint": f"/api/v1/skill-packs/{pack.skill_pack_id}/debugger"},
                    ],
                }
                for pack in packs
            ],
        }

    def _enabled(self) -> bool:
        config = load_yaml_file(PATHS.config_root / "skills" / "skill_packs.yaml", critical=False, root=PATHS.config_root)
        return bool(config.get("skill_packs_enabled", True)) if isinstance(config, dict) else True

    def _load_manifest(self, path: Path) -> SkillPackManifest:
        return SkillPackManifest(**(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))

    def _write_index(self) -> None:
        packs = []
        if self.root.exists():
            for path in self.root.glob("*/pack.yaml"):
                try:
                    pack = self._load_manifest(path)
                except Exception:
                    continue
                packs.append({
                    "skill_pack_id": pack.skill_pack_id,
                    "slug": pack.slug,
                    "display_name": pack.display_name,
                    "version": pack.version,
                    "status": pack.status,
                    "category": pack.category,
                    "risk_level": pack.risk_level,
                })
        self.index_path.write_text(json.dumps({"schema_version": 1, "updated_at": utc_now_iso(), "packs": packs}, indent=2, ensure_ascii=True), encoding="utf-8")


class SkillPackExecutionService:
    def __init__(
        self,
        *,
        registry: SkillPackRegistry | None = None,
        skill_execution: SkillExecutionService | None = None,
        executions_root: Path | None = None,
    ) -> None:
        self.registry = registry or SkillPackRegistry()
        self.skill_execution = skill_execution or SkillExecutionService(registry=self.registry.skill_registry)
        self.executions_root = executions_root or PATHS.project_root / "data" / "runtime" / "skill_packs" / "executions"
        self.executions_root.mkdir(parents=True, exist_ok=True)

    def execute(self, request: SkillPackExecutionRequest) -> SkillPackExecutionResult:
        started_at = utc_now_iso()
        try:
            pack = self.registry.get(request.skill_pack_id)
        except KeyError:
            result = SkillPackExecutionResult(
                skill_pack_execution_id=request.skill_pack_execution_id,
                skill_pack_id=request.skill_pack_id,
                skill_pack_version=request.skill_pack_version or "unknown",
                status="blocked",
                errors=["skill_pack_not_found"],
                started_at=started_at,
                completed_at=utc_now_iso(),
            )
            self._save(result)
            return result
        validation = self.registry.validate_pack(pack)
        if not validation.valid:
            result = SkillPackExecutionResult(
                skill_pack_execution_id=request.skill_pack_execution_id,
                skill_pack_id=pack.skill_pack_id,
                skill_pack_version=pack.version,
                status="blocked",
                errors=validation.reason_codes,
                warnings=validation.warnings,
                started_at=started_at,
                completed_at=utc_now_iso(),
                evidence_refs=[f"skill_pack:{pack.skill_pack_id}"],
            )
            self._save(result)
            return result
        selected = [request.requested_skill_id] if request.requested_skill_id else list(pack.included_skills)
        if request.requested_skill_id and request.requested_skill_id not in pack.included_skills:
            result = SkillPackExecutionResult(
                skill_pack_execution_id=request.skill_pack_execution_id,
                skill_pack_id=pack.skill_pack_id,
                skill_pack_version=pack.version,
                status="blocked",
                selected_skills=[],
                errors=["requested_skill_not_in_pack"],
                started_at=started_at,
                completed_at=utc_now_iso(),
                evidence_refs=[f"skill_pack:{pack.skill_pack_id}"],
            )
            self._save(result)
            return result

        result = SkillPackExecutionResult(
            skill_pack_execution_id=request.skill_pack_execution_id,
            skill_pack_id=pack.skill_pack_id,
            skill_pack_version=pack.version,
            status="running",
            selected_skills=selected,
            warnings=[*validation.warnings],
            started_at=started_at,
            metadata_sanitized=redact_payload({
                **request.metadata_sanitized,
                "requesting_agent_id": request.requesting_agent_id,
                "session_id": request.session_id,
                "execution_mode": request.execution_mode,
                "autopilot_run_id": request.autopilot_run_id,
            }),
        )
        self._save(result)

        for skill_id in selected:
            skill_request = SkillExecutionRequest(
                skill_id=skill_id,
                requesting_agent_id=request.requesting_agent_id,
                session_id=request.session_id,
                run_id=request.run_id,
                project_profile_id=request.project_profile_id,
                workspace_profile_id=request.workspace_id,
                sandbox_workspace_id=request.sandbox_workspace_id,
                sandbox_task_id=request.sandbox_task_id,
                user_goal=request.user_goal,
                inputs=request.inputs,
                execution_mode=request.execution_mode,
                requested_capabilities=request.requested_capabilities,
                metadata_sanitized=redact_payload({
                    **request.metadata_sanitized,
                    "skill_pack_id": pack.skill_pack_id,
                    "skill_pack_execution_id": request.skill_pack_execution_id,
                    "autopilot_run_id": request.autopilot_run_id,
                }),
            )
            skill_result = self.skill_execution.execute(skill_request)
            result.skill_execution_ids.append(skill_result.skill_execution_id)
            result.artifacts.extend(skill_result.output_artifact_refs)
            result.reports.extend(skill_result.report_refs)
            result.validation_ids.extend(skill_result.validation_ids)
            result.policy_decision_ids.extend(skill_result.policy_decision_ids)
            result.evidence_refs.extend(skill_result.evidence_refs)
            if skill_result.warnings:
                result.warnings.extend([f"{skill_id}:{item}" for item in skill_result.warnings])
            if skill_result.status in {"blocked", "failed", "validation_failed"}:
                result.status = skill_result.status
                result.errors.extend([f"{skill_id}:{item}" for item in (skill_result.blocked_reasons or skill_result.errors or [skill_result.status])])
                break

        if result.status == "running":
            result.status = "completed_with_warnings" if result.warnings else "completed"
        if result.status == "completed" and not result.evidence_refs:
            result.status = "completed_with_warnings"
            result.warnings.append("completed_without_downstream_evidence_refs")
        result.evidence_refs = sorted(set([*result.evidence_refs, f"skill_pack:{pack.skill_pack_id}", f"skill_pack_execution:{request.skill_pack_execution_id}"]))
        result.artifacts = sorted(set(result.artifacts))
        result.reports = sorted(set(result.reports))
        result.validation_ids = sorted(set(result.validation_ids))
        result.policy_decision_ids = sorted(set(result.policy_decision_ids))
        result.completed_at = utc_now_iso()
        self._save(result)
        return result

    def get(self, skill_pack_execution_id: str) -> SkillPackExecutionResult | None:
        path = self.executions_root / f"{skill_pack_execution_id}.json"
        if not path.exists():
            return None
        return SkillPackExecutionResult(**json.loads(path.read_text(encoding="utf-8")))

    def trace(self, skill_pack_execution_id: str) -> dict[str, Any] | None:
        result = self.get(skill_pack_execution_id)
        if result is None:
            return None
        return {
            "status": "ok",
            "skill_pack_execution": result.model_dump(),
            "raw_default_visible": False,
            "filters": {
                "skill_pack_id": result.skill_pack_id,
                "skill_execution_ids": result.skill_execution_ids,
                "status": result.status,
            },
        }

    def _save(self, result: SkillPackExecutionResult) -> None:
        self.executions_root.mkdir(parents=True, exist_ok=True)
        (self.executions_root / f"{result.skill_pack_execution_id}.json").write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=True, indent=2), encoding="utf-8")
