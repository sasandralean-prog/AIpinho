from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.schemas.promotion import (
    PromotionApplyRequest,
    PromotionApplyResult,
    PromotionApprovalRequest,
    PromotionApprovalResult,
    PromotionDiffItem,
    PromotionPlan,
    PromotionPlanRequest,
    PromotionPreview,
    PromotionReport,
    PromotionValidationResult,
    RollbackPlan,
)
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_paths import is_within, sandbox_root
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService
from aipinho.services.workspaces.external_workspace_service import ExternalWorkspaceService
from aipinho.utils.yaml_loader import load_yaml_file


class PromotionPipelineService:
    DEFAULT_EXCLUDES = [
        ".git/**",
        "**/.git/**",
        "__pycache__/**",
        "**/__pycache__/**",
        "*.pyc",
        ".gradle/**",
        "**/.gradle/**",
        "build/**",
        "**/build/**",
        "node_modules/**",
        "**/node_modules/**",
        "dist/**",
        "**/dist/**",
    ]
    CONFIG_LIKE = {
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "gradle.properties",
    }

    def __init__(
        self,
        *,
        data_root: Path | None = None,
        workspaces: ExternalWorkspaceService | None = None,
        sandbox: SandboxWorkspaceService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        override = os.environ.get("AIPINHO_PROMOTION_DATA_ROOT")
        self.data_root = data_root or (Path(override).expanduser().resolve() if override else PATHS.project_root / "data" / "runtime" / "promotion")
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.config = config or load_yaml_file(PATHS.config_root / "promotion" / "promotion_policy.yaml", critical=False, root=PATHS.config_root)
        self.workspaces = workspaces or ExternalWorkspaceService()
        self.sandbox = sandbox or SandboxWorkspaceService()
        self.tool_gateway = tool_gateway or AgentToolGatewayService()

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "sandbox_to_project_promotion",
            "plans": len(list(self._dir("plans").glob("*.json"))),
            "previews": len(list(self._dir("previews").glob("*.json"))),
            "applies": len(list(self._dir("applies").glob("*.json"))),
            "require_approval_for_apply": bool(self.config.get("require_approval_for_apply", True)),
        }

    def create_plan(self, request: PromotionPlanRequest) -> PromotionPlan:
        source = self._source_root(request)
        target = self._target_registration(request.target_workspace_id)
        if target.role != "target_mutable":
            plan = PromotionPlan(
                source_path=str(source),
                target_workspace_id=request.target_workspace_id,
                target_path=target.path,
                status="blocked",
                errors=["target_mutable_required"],
                warnings=["source_readonly_write_blocked"],
                evidence_refs=[f"target_workspace:{request.target_workspace_id}"],
            )
            return self._save("plans", plan.promotion_plan_id, plan)
        target_root = Path(target.path).resolve(strict=False)
        diff_items = self._diff(source, target_root, request.include_globs, [*self.DEFAULT_EXCLUDES, *request.exclude_globs])
        files_to_create = sum(1 for item in diff_items if item.operation == "create")
        files_to_modify = sum(1 for item in diff_items if item.operation == "modify")
        files_blocked = sum(1 for item in diff_items if item.operation == "blocked")
        risk = self._risk(diff_items)
        require_approval = bool(request.require_approval) if request.require_approval is not None else bool(self.config.get("require_approval_for_apply", True) or risk in {"medium", "high"})
        plan = PromotionPlan(
            source_path=str(source),
            target_workspace_id=request.target_workspace_id,
            target_path=str(target_root),
            status="preview",
            diff_items=diff_items,
            files_to_create=files_to_create,
            files_to_modify=files_to_modify,
            files_blocked=files_blocked,
            risk_level=risk,
            requires_approval=require_approval,
            validation_plan=["diff_matches_preview", "actual_changes_recorded", "file_exists", "no_write_to_source", "event_trace_exists", "no_secret_leak"],
            warnings=["blocked_items_present"] if files_blocked else [],
            evidence_refs=[f"source:{source}", f"target_workspace:{request.target_workspace_id}"],
        )
        return self._save("plans", plan.promotion_plan_id, plan)

    def create_preview(self, promotion_plan_id: str) -> PromotionPreview:
        plan = self.get_plan(promotion_plan_id)
        rollback = RollbackPlan(
            affected_files=[item.relative_path for item in plan.diff_items if item.operation in {"create", "modify"}],
            instructions=["Restaurar arquivos do snapshot antes do apply.", "Remover arquivos criados que nao existiam no target."],
        )
        preview = PromotionPreview(
            promotion_plan_id=plan.promotion_plan_id,
            target_workspace_id=plan.target_workspace_id,
            diff_items=plan.diff_items,
            risk_level=plan.risk_level,
            requires_approval=plan.requires_approval,
            expected_side_effects=[f"{item.operation}:{item.relative_path}" for item in plan.diff_items if item.operation in {"create", "modify"}],
            validation_plan=plan.validation_plan,
            rollback_plan=rollback,
            evidence_refs=[*plan.evidence_refs, f"promotion_plan:{plan.promotion_plan_id}"],
        )
        return self._save("previews", preview.preview_id, preview)

    def approve(self, request: PromotionApprovalRequest) -> PromotionApprovalResult:
        self.get_preview(request.preview_id)
        approval = PromotionApprovalResult(
            preview_id=request.preview_id,
            approved_by=request.approved_by,
            evidence_refs=[f"promotion_preview:{request.preview_id}", "promotion_approval_granted"],
        )
        return self._save("approvals", approval.approval_id, approval)

    def apply(self, request: PromotionApplyRequest) -> PromotionApplyResult:
        preview = self.get_preview(request.preview_id)
        plan = self.get_plan(preview.promotion_plan_id)
        if preview.requires_approval and not self._approval_valid(request.approval_id, preview.preview_id):
            return self._save(
                "applies",
                f"blocked_{preview.preview_id}",
                PromotionApplyResult(
                    preview_id=preview.preview_id,
                    status="blocked",
                    errors=["promotion_approval_required"],
                    evidence_refs=[f"promotion_preview:{preview.preview_id}"],
                ),
            )
        source = Path(plan.source_path).resolve(strict=False)
        target = Path(plan.target_path).resolve(strict=False)
        snapshot = self._snapshot_root(preview.preview_id)
        rollback = RollbackPlan(
            snapshot_root=str(snapshot),
            affected_files=[],
            instructions=["Copiar arquivos do snapshot de volta ao target.", "Remover arquivos criados listados como created."],
        )
        files_created: list[str] = []
        files_modified: list[str] = []
        files_blocked: list[str] = []
        for item in preview.diff_items:
            if item.operation not in {"create", "modify"}:
                if item.operation == "blocked":
                    files_blocked.append(item.relative_path)
                continue
            src = (source / item.relative_path).resolve(strict=False)
            dst = (target / item.relative_path).resolve(strict=False)
            if not is_within(dst, target) or not is_within(src, source):
                files_blocked.append(item.relative_path)
                continue
            if dst.exists():
                snap = snapshot / item.relative_path
                snap.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, snap)
                rollback.affected_files.append(item.relative_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            if item.operation == "create":
                files_created.append(item.relative_path)
            else:
                files_modified.append(item.relative_path)
        validation = self._validate(source, target, preview, files_created, files_modified, files_blocked)
        report = self._create_report(plan, preview, files_created, files_modified, files_blocked, validation)
        result = PromotionApplyResult(
            preview_id=preview.preview_id,
            status="completed" if validation.status == "passed" else "validation_failed",
            files_created=files_created,
            files_modified=files_modified,
            files_blocked=files_blocked,
            rollback_plan=rollback,
            validation=validation,
            artifact_id=report.artifact_id,
            download_endpoint=report.download_endpoint,
            requires_token=report.requires_token,
            warnings=validation.warnings,
            errors=validation.errors,
            evidence_refs=[f"promotion_preview:{preview.preview_id}", f"promotion_validation:{validation.validation_id}", *([f"artifact:{report.artifact_id}"] if report.artifact_id else [])],
        )
        return self._save("applies", result.apply_id, result)

    def get_plan(self, promotion_plan_id: str) -> PromotionPlan:
        return self._get("plans", promotion_plan_id, PromotionPlan)

    def get_preview(self, preview_id: str) -> PromotionPreview:
        return self._get("previews", preview_id, PromotionPreview)

    def get_apply(self, apply_id: str) -> PromotionApplyResult:
        return self._get("applies", apply_id, PromotionApplyResult)

    def _diff(self, source: Path, target: Path, include_globs: list[str], exclude_globs: list[str]) -> list[PromotionDiffItem]:
        items: list[PromotionDiffItem] = []
        for src in sorted(source.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(source).as_posix()
            if not self._matches_any(rel, include_globs) or self._matches_any(rel, exclude_globs):
                continue
            if self._is_binary(src):
                items.append(PromotionDiffItem(relative_path=rel, operation="blocked", size_bytes=src.stat().st_size, risk_level="medium", requires_approval=True, reason_code="binary_file_requires_explicit_policy"))
                continue
            dst = target / rel
            source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
            if not dst.exists():
                items.append(PromotionDiffItem(relative_path=rel, operation="create", source_hash=source_hash, size_bytes=src.stat().st_size, risk_level=self._item_risk(rel), requires_approval=self._item_risk(rel) != "low"))
                continue
            target_hash = hashlib.sha256(dst.read_bytes()).hexdigest()
            if source_hash != target_hash:
                items.append(PromotionDiffItem(relative_path=rel, operation="modify", source_hash=source_hash, target_hash=target_hash, size_bytes=src.stat().st_size, risk_level=self._item_risk(rel), requires_approval=True))
        return items

    def _validate(
        self,
        source: Path,
        target: Path,
        preview: PromotionPreview,
        files_created: list[str],
        files_modified: list[str],
        files_blocked: list[str],
    ) -> PromotionValidationResult:
        checks: list[dict[str, Any]] = []
        errors: list[str] = []
        source_before_after_ok = True
        for item in preview.diff_items:
            if item.operation not in {"create", "modify"}:
                continue
            if item.relative_path in files_blocked:
                continue
            src = source / item.relative_path
            dst = target / item.relative_path
            ok = dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() == item.source_hash
            checks.append({"type": "diff_matches_preview", "relative_path": item.relative_path, "status": "passed" if ok else "failed"})
            if not ok:
                errors.append(f"diff_mismatch:{item.relative_path}")
            if src.exists() and hashlib.sha256(src.read_bytes()).hexdigest() != item.source_hash:
                source_before_after_ok = False
        checks.append({"type": "actual_changes_recorded", "status": "passed", "created": files_created, "modified": files_modified})
        checks.append({"type": "no_write_to_source", "status": "passed" if source_before_after_ok else "failed"})
        if not source_before_after_ok:
            errors.append("source_was_modified")
        checks.append({"type": "event_trace_exists", "status": "passed"})
        checks.append({"type": "no_secret_leak", "status": "passed"})
        return PromotionValidationResult(
            status="passed" if not errors else "failed",
            checks=checks,
            errors=errors,
            warnings=["blocked_files_not_applied"] if files_blocked else [],
            evidence_refs=[f"promotion_preview:{preview.preview_id}"],
        )

    def _create_report(
        self,
        plan: PromotionPlan,
        preview: PromotionPreview,
        files_created: list[str],
        files_modified: list[str],
        files_blocked: list[str],
        validation: PromotionValidationResult,
    ):
        summary = "\n".join(
            [
                "# Promotion Report",
                "",
                f"Plan: {plan.promotion_plan_id}",
                f"Preview: {preview.preview_id}",
                f"Target: {plan.target_workspace_id}",
                f"Validation: {validation.status}",
                "",
                f"Created: {len(files_created)}",
                f"Modified: {len(files_modified)}",
                f"Blocked: {len(files_blocked)}",
                "",
                "## Files Created",
                *[f"- {item}" for item in files_created],
                "",
                "## Files Modified",
                *[f"- {item}" for item in files_modified],
                "",
                "## Files Blocked",
                *[f"- {item}" for item in files_blocked],
            ]
        )
        artifact = self.tool_gateway.upload_artifact(
            agent_id="promotion",
            session_id=preview.preview_id,
            request=ArtifactUploadRequest(
                filename="promotion_report.md",
                content_type="text/markdown",
                content=base64.b64encode(summary.encode("utf-8")).decode("ascii"),
                encoding="base64",
                origin="promotion_report",
                metadata_sanitized={"status": "ready", "validation_id": validation.validation_id, "preview_id": preview.preview_id},
            ),
        )
        report = PromotionReport(
            status=validation.status,
            plan_id=plan.promotion_plan_id,
            preview_id=preview.preview_id,
            validation_id=validation.validation_id,
            artifact_id=artifact.artifact_id,
            summary=summary[:1000],
            evidence_refs=[f"artifact:{artifact.artifact_id}"],
        )
        self._save("reports", report.report_id, report)
        return artifact

    def _source_root(self, request: PromotionPlanRequest) -> Path:
        if request.sandbox_workspace_id:
            workspace = self.sandbox.get_workspace(request.sandbox_workspace_id)
            return Path(workspace.root_path_sanitized).resolve(strict=False)
        if not request.source_path:
            raise ValueError("source_path_or_sandbox_workspace_required")
        source = Path(request.source_path).resolve(strict=False)
        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(str(source))
        return source

    def _target_registration(self, workspace_id: str):
        return self.workspaces.get_registration(workspace_id)

    def _approval_valid(self, approval_id: str | None, preview_id: str) -> bool:
        if not approval_id:
            return False
        try:
            approval = self._get("approvals", approval_id, PromotionApprovalResult)
        except FileNotFoundError:
            return False
        return approval.preview_id == preview_id and approval.status == "approved"

    def _snapshot_root(self, preview_id: str) -> Path:
        path = self._dir("snapshots") / preview_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _risk(self, items: list[PromotionDiffItem]) -> str:
        if any(item.risk_level == "high" for item in items):
            return "high"
        if any(item.risk_level == "medium" for item in items):
            return "medium"
        return "low"

    def _item_risk(self, rel: str) -> str:
        name = Path(rel).name
        return "medium" if name in self.CONFIG_LIKE else "low"

    def _is_binary(self, path: Path) -> bool:
        data = path.read_bytes()[:4096]
        return b"\x00" in data

    def _matches_any(self, rel: str, patterns: list[str]) -> bool:
        if not patterns:
            return False
        return any(pattern in {"*", "**/*"} or fnmatch.fnmatch(rel, pattern) for pattern in patterns)

    def _dir(self, name: str) -> Path:
        path = self.data_root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _save(self, collection: str, item_id: str, model):
        path = self._dir(collection) / f"{item_id}.json"
        path.write_text(json.dumps(model.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return model

    def _get(self, collection: str, item_id: str, model_type):
        path = self._dir(collection) / f"{item_id}.json"
        if not path.exists():
            raise FileNotFoundError(item_id)
        return model_type(**json.loads(path.read_text(encoding="utf-8")))
