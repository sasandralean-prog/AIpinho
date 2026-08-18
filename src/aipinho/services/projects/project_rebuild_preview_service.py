from __future__ import annotations

import difflib
import os
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.diff_preview import DiffPreview
from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.projects.project_rebuild_preview import (
    ProjectRebuildFileEntry,
    ProjectRebuildPreviewRequest,
    ProjectRebuildPreviewResult,
)
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.patch_file_reader import PatchFileReader
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.patching.patch_risk_service import PatchRiskService
from aipinho.services.patching.patch_target_guard import PatchTargetGuard
from aipinho.services.patching.patch_test_recommendation_service import PatchTestRecommendationService
from aipinho.services.patching.patch_validation_service import PatchValidationService
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from aipinho.services.patching.rollback_note_service import RollbackNoteService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file


class ProjectRebuildPreviewService:
    """Creates governed patch previews for source-to-target project rebuilds."""

    def __init__(
        self,
        run_store: TaskRunStore | None = None,
        plan_store: PatchPlanStore | None = None,
        workspace_contracts: WorkspaceRoleContractService | None = None,
    ) -> None:
        self.policy = load_yaml_file(
            PATHS.config_root / "projects" / "project_rebuild_policy.yaml",
            critical=True,
            root=PATHS.config_root / "projects",
        )
        self.run_store = run_store or TaskRunStore()
        self.plan_store = plan_store or PatchPlanStore()
        self.workspace_contracts = workspace_contracts or WorkspaceRoleContractService().load()
        self.target_guard = PatchTargetGuard()
        self.file_reader = PatchFileReader()
        self.risk_service = PatchRiskService()
        self.rollback_service = RollbackNoteService()
        self.tests_service = PatchTestRecommendationService()
        self.validation_service = PatchValidationService()

    def create_preview(self, request: ProjectRebuildPreviewRequest) -> ProjectRebuildPreviewResult:
        operation_id = request.operation_id or f"project_rebuild_{uuid4().hex}"
        trace: list[dict[str, object]] = [
            {"stage": "project_rebuild_preview", "decision": "started", "operation_id": operation_id}
        ]
        if not self._settings().get("enabled", True):
            return self._blocked(operation_id, request, ["project_rebuild_disabled"], trace=trace)

        source_workspace, source_run_id, source_warnings = self._resolve_source(request)
        target_workspace = request.target_workspace
        source_decision = self.workspace_contracts.resolve(source_workspace, required=True)
        target_decision = self.workspace_contracts.resolve(target_workspace, required=True)
        trace.extend(source_decision.trace)
        trace.extend(target_decision.trace)

        blocked: list[str] = []
        warnings: list[str] = list(source_warnings)
        if source_decision.status != "allowed" or source_decision.contract is None:
            blocked.append(source_decision.reason)
        elif not source_decision.contract.read_allowed:
            blocked.append("source_workspace_read_denied")
        if target_decision.status != "allowed" or target_decision.contract is None:
            blocked.append(target_decision.reason)
        elif not target_decision.contract.patch_allowed:
            blocked.append("target_workspace_patch_denied")
        if source_workspace and target_workspace and self._same_path(source_workspace, target_workspace):
            blocked.append("source_and_target_must_differ")
        if blocked:
            return self._blocked(
                operation_id,
                request,
                blocked,
                source_workspace=source_workspace,
                source_run_id=source_run_id,
                warnings=warnings,
                trace=trace,
            )

        files, omitted = self._collect_files(Path(source_workspace), Path(target_workspace))
        if not files:
            return self._blocked(
                operation_id,
                request,
                ["no_rebuild_files_selected"],
                source_workspace=source_workspace,
                source_run_id=source_run_id,
                warnings=warnings,
                omitted_files=omitted,
                trace=trace,
            )

        plan = self._build_patch_plan(
            operation_id=operation_id,
            request=request,
            source_workspace=source_workspace,
            source_run_id=source_run_id,
            target_workspace=target_workspace,
            files=files,
            warnings=warnings,
        )
        quality = PatchQualityGateService(plan_store=self.plan_store).validate_plan(plan.plan_id)
        approval_id = None
        if quality and quality.status == "passed" and bool(self._settings().get("request_approval_when_quality_passes", True)):
            approval = PatchApplyService(plan_store=self.plan_store).request_approval(plan.plan_id)
            approval.session_id = request.session_id
            PatchApplyService().approval_service.store.save(approval)
            approval_id = approval.approval_id
        refreshed = self.plan_store.get_plan(plan.plan_id) or plan
        status = "pending_approval" if approval_id else ("preview" if quality and quality.safe_for_future_apply_review else "blocked")
        blocked_reasons = list(refreshed.blocked_reasons)
        if quality and quality.status not in {"passed", "passed_with_warnings"}:
            blocked_reasons.append(f"patch_quality_not_passed:{quality.status}")
        return ProjectRebuildPreviewResult(
            status=status,
            operation_id=operation_id,
            source_workspace=source_workspace,
            target_workspace=target_workspace,
            source_run_id=source_run_id,
            plan_id=plan.plan_id,
            quality_id=quality.quality_id if quality else None,
            approval_id=approval_id,
            files=files,
            omitted_files=omitted,
            warnings=list(dict.fromkeys([*warnings, *refreshed.warnings])),
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            message=self._message(status, files, omitted, quality_id=quality.quality_id if quality else None, approval_id=approval_id),
            trace=[*trace, {"stage": "project_rebuild_preview", "decision": status, "plan_id": plan.plan_id}],
        )

    def _settings(self) -> dict[str, object]:
        value = self.policy.get("project_rebuild", {})
        return value if isinstance(value, dict) else {}

    def _selection(self) -> dict[str, object]:
        value = self.policy.get("selection", {})
        return value if isinstance(value, dict) else {}

    def _resolve_source(self, request: ProjectRebuildPreviewRequest) -> tuple[str | None, str | None, list[str]]:
        if request.source_workspace:
            return request.source_workspace, request.source_run_id, []
        if request.source_run_id:
            run = self.run_store.get_run(request.source_run_id)
            if run is not None:
                return run.workspace, run.run_id, []
        if request.session_id:
            for run in self.run_store.list_runs(session_id=request.session_id, status="completed", contract_type="readonly_analysis", limit=20):
                refs = run.intent_map.get("workspace_references", [])
                if isinstance(refs, list):
                    for ref in refs:
                        if isinstance(ref, dict) and ref.get("role") == "source_readonly" and ref.get("path"):
                            return str(ref["path"]), run.run_id, []
                if run.workspace:
                    return run.workspace, run.run_id, ["source_inferred_from_latest_readonly_run"]
        return None, None, ["source_workspace_not_found_in_session"]

    def _collect_files(self, source_root: Path, target_root: Path) -> tuple[list[ProjectRebuildFileEntry], list[ProjectRebuildFileEntry]]:
        selection = self._selection()
        blocked_dirs = {str(item).lower() for item in selection.get("blocked_dirs", []) or []}
        blocked_exts = {str(item).lower() for item in selection.get("blocked_extensions", []) or []}
        allowed_exts = {str(item).lower() for item in selection.get("allowed_extensions", []) or []}
        include_hidden = bool(self._settings().get("include_hidden_files", False))
        max_files = int(self._settings().get("max_files_per_preview", 10))
        max_total_bytes = int(self._settings().get("max_total_bytes_per_preview", 250000))
        max_file_bytes = int(self._settings().get("max_file_bytes", 100000))
        candidates: list[tuple[int, Path]] = []
        omitted: list[ProjectRebuildFileEntry] = []
        for path in sorted(source_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source_root)
            rel_parts = [part.lower() for part in rel.parts]
            if any(part in blocked_dirs for part in rel_parts):
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["blocked_directory"]))
                continue
            if not include_hidden and any(part.startswith(".") for part in rel_parts):
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["hidden_path"]))
                continue
            suffix = path.suffix.lower()
            if suffix in blocked_exts or (allowed_exts and suffix not in allowed_exts):
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["extension_not_allowed"]))
                continue
            if path.stat().st_size > max_file_bytes:
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["file_too_large"]))
                continue
            target_path = target_root / rel
            if target_path.is_file() and self._same_text_content(path, target_path):
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["already_synchronized"]))
                continue
            candidates.append((self._priority(rel), path))
        selected: list[ProjectRebuildFileEntry] = []
        total = 0
        for _priority, path in sorted(candidates, key=lambda item: (item[0], str(item[1]).lower())):
            size = path.stat().st_size
            if len(selected) >= max_files:
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["preview_file_limit_reached"]))
                continue
            if total + size > max_total_bytes:
                omitted.append(self._entry(source_root, target_root, path, "omitted", ["preview_byte_limit_reached"]))
                continue
            selected.append(self._entry(source_root, target_root, path, "included", []))
            total += size
        return selected, omitted

    def _priority(self, rel: Path) -> int:
        normalized = rel.as_posix()
        priority_files = [str(item).replace("\\", "/") for item in self._selection().get("priority_files", []) or []]
        if normalized in priority_files:
            return priority_files.index(normalized)
        if normalized.startswith("src/"):
            return 100
        return 200

    def _entry(self, source_root: Path, target_root: Path, path: Path, status: str, reasons: list[str]) -> ProjectRebuildFileEntry:
        rel = path.relative_to(source_root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
            lines = len(content.splitlines())
        except Exception:
            lines = 0
        return ProjectRebuildFileEntry(
            relative_path=rel,
            source_path=str(path),
            target_path=str(target_root / rel),
            size_bytes=path.stat().st_size if path.exists() else 0,
            line_count=lines,
            status=status,
            blocked_reasons=reasons,
        )

    def _build_patch_plan(
        self,
        *,
        operation_id: str,
        request: ProjectRebuildPreviewRequest,
        source_workspace: str,
        source_run_id: str | None,
        target_workspace: str,
        files: list[ProjectRebuildFileEntry],
        warnings: list[str],
    ) -> PatchPlan:
        plan_id = f"patch_plan_{uuid4().hex}"
        affected: list[AffectedFile] = []
        evidence: list[PatchEvidence] = []
        hunks: list[PatchHunk] = []
        diff_parts: list[str] = []
        added = 0
        removed = 0
        for index, file in enumerate(files, start=1):
            checked = self.target_guard.validate(target_workspace, file.relative_path)
            checked, current_content = self.file_reader.read(checked)
            affected.append(checked)
            source_content = Path(file.source_path).read_text(encoding="utf-8")
            evidence_id = f"project_rebuild_evidence_{index:03d}"
            evidence.append(
                PatchEvidence(
                    evidence_id=evidence_id,
                    source_type="source_workspace_file",
                    source_id=source_run_id or operation_id,
                    source_path=file.relative_path,
                    excerpt=f"Source file selected for governed rebuild: {file.relative_path}",
                    confidence=0.9,
                )
            )
            hunk = PatchHunk(
                hunk_id=f"patch_hunk_{uuid4().hex}",
                file_path=file.relative_path,
                original=current_content,
                replacement=source_content,
                reason="Create or synchronize target file from selected source workspace evidence.",
                evidence_ids=[evidence_id],
                confidence=0.82,
            )
            hunks.append(hunk)
            file_diff = "\n".join(
                difflib.unified_diff(
                    current_content.splitlines(),
                    source_content.splitlines(),
                    fromfile=f"a/{file.relative_path}",
                    tofile=f"b/{file.relative_path}",
                    lineterm="",
                )
            )
            diff_parts.append(file_diff)
            added += sum(1 for line in file_diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
            removed += sum(1 for line in file_diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        diff_text = "\n".join(part for part in diff_parts if part.strip())
        diff = DiffProposal(
            proposal_id=f"diff_proposal_{uuid4().hex}",
            plan_id=plan_id,
            status="generated" if diff_text else "invalid",
            diff=DiffPreview(diff_text=diff_text, truncated=False, chars=len(diff_text), added_lines=added, removed_lines=removed),
            blocked_reasons=[] if diff_text else ["empty_diff"],
        )
        risk = self.risk_service.assess(affected, evidence_count=len(evidence), diff_chars=len(diff_text))
        rollback = self.rollback_service.build(affected)
        tests = self.tests_service.recommend(affected)
        validation = self.validation_service.validate(
            evidence=evidence,
            diff=diff,
            risk=risk,
            rollback_notes=rollback,
            test_recommendations=tests,
        )
        risk_block_reasons = risk.reasons if risk.blocked else []
        blocked_candidates = [
            *[reason for file in affected for reason in file.blocked_reasons],
            *validation.blocked_reasons,
            *risk_block_reasons,
        ]
        blocked = list(dict.fromkeys(reason for reason in blocked_candidates if reason))
        status = "blocked" if blocked or risk.blocked else validation.status
        if status == "ready_for_review" and risk.needs_review:
            status = "needs_review"
        now = utc_now()
        plan = PatchPlan(
            plan_id=plan_id,
            status=status,
            workspace=target_workspace,
            source_type="project_rebuild",
            source_id=source_run_id or operation_id,
            objective=request.prompt or "Governed project rebuild from source workspace evidence.",
            affected_files=affected,
            evidence=evidence,
            hunks=hunks,
            diff_proposal=diff,
            risk=risk,
            validation=validation,
            rollback_notes=rollback,
            test_recommendations=tests,
            created_at=now,
            updated_at=now,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=blocked,
            trace=[
                "project_rebuild_preview_started",
                f"source_workspace:{source_workspace}",
                f"target_workspace:{target_workspace}",
                f"files_selected:{len(files)}",
                f"project_rebuild_preview_finished:{status}",
            ],
        )
        return self.plan_store.save_plan(plan)

    def _message(
        self,
        status: str,
        files: list[ProjectRebuildFileEntry],
        omitted: list[ProjectRebuildFileEntry],
        *,
        quality_id: str | None,
        approval_id: str | None,
    ) -> str:
        file_label = "arquivo" if len(files) == 1 else "arquivos"
        if status == "pending_approval":
            return (
                f"Criei um preview governado para reconstruir o projeto no workspace alvo com {len(files)} {file_label}. "
                "Nada foi escrito ainda. O Patch Quality Gate passou e existe uma aprovacao pendente para aplicar o patch."
            )
        if status == "preview":
            return (
                f"Criei um preview governado com {len(files)} {file_label}. "
                "Nada foi escrito ainda; revise o diff e os avisos antes de pedir approval."
            )
        return (
            "Nao consegui criar um preview aplicavel para rebuild do projeto. "
            f"Arquivos selecionados: {len(files)}; omitidos: {len(omitted)}; quality_id: {quality_id or 'indisponivel'}."
        )

    def _blocked(
        self,
        operation_id: str,
        request: ProjectRebuildPreviewRequest,
        blocked_reasons: list[str],
        *,
        source_workspace: str | None = None,
        source_run_id: str | None = None,
        warnings: list[str] | None = None,
        omitted_files: list[ProjectRebuildFileEntry] | None = None,
        trace: list[dict[str, object]] | None = None,
    ) -> ProjectRebuildPreviewResult:
        return ProjectRebuildPreviewResult(
            status="blocked",
            operation_id=operation_id,
            source_workspace=source_workspace,
            target_workspace=request.target_workspace,
            source_run_id=source_run_id,
            omitted_files=omitted_files or [],
            warnings=warnings or [],
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            message="O preview de rebuild foi bloqueado antes de qualquer escrita.",
            trace=trace or [],
        )

    def _same_path(self, left: str, right: str) -> bool:
        try:
            return os.path.normcase(str(Path(left).resolve(strict=False))) == os.path.normcase(str(Path(right).resolve(strict=False)))
        except Exception:
            return left == right

    def _same_text_content(self, left: Path, right: Path) -> bool:
        try:
            left_text = left.read_text(encoding="utf-8")
            right_text = right.read_text(encoding="utf-8")
        except Exception:
            return False
        return self._normalize_text_content(left_text) == self._normalize_text_content(right_text)

    def _normalize_text_content(self, text: str) -> str:
        return text.replace("\r\n", "\n").replace("\r", "\n")
