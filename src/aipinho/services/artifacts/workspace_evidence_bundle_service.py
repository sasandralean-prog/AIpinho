from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.artifacts.workspace_evidence_bundle import WorkspaceEvidenceBundleRequest, WorkspaceEvidenceBundleResult
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_pass_runner import RolePassRunner
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class WorkspaceEvidenceBundleService:
    """Creates a governed report plus a validated ZIP from explicit workspace evidence."""

    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        gateway: AgentToolGatewayService | None = None,
        resolver: AgentToolWorkspaceResolver | None = None,
        reporter: RolePassRunner | None = None,
        policy: dict[str, Any] | None = None,
    ) -> None:
        self.kernel = kernel or AgentSessionKernelService()
        self.gateway = gateway or AgentToolGatewayService(kernel=self.kernel)
        self.resolver = resolver or self.gateway.resolver
        self.reporter = reporter or RolePassRunner()
        self.bindings = RoleModelBindingService()
        self.secret_guard = SecretGuardService()
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "artifacts" / "workspace_evidence_bundle_policy.yaml",
            critical=True,
            root=PATHS.config_root / "artifacts",
        )

    @property
    def settings(self) -> dict[str, Any]:
        value = self.policy.get("workspace_evidence_bundle", {})
        return value if isinstance(value, dict) else {}

    def execute(self, request: WorkspaceEvidenceBundleRequest) -> WorkspaceEvidenceBundleResult:
        if not self.settings.get("enabled", True):
            return WorkspaceEvidenceBundleResult(status="blocked", reason_code="workspace_evidence_bundle_disabled")
        workspace = self._resolve_workspace(request.workspace_ref)
        if not workspace.allowed or not workspace.root_path_sanitized:
            return WorkspaceEvidenceBundleResult(status="blocked", reason_code=workspace.reason_code)
        root = Path(workspace.resolved_path_sanitized or workspace.root_path_sanitized).resolve()
        summary_relative = self._safe_relative(request.summary_relative_path)
        archive_relative = self._safe_relative(request.archive_relative_path)
        if summary_relative is None or archive_relative is None:
            return WorkspaceEvidenceBundleResult(status="blocked", reason_code="bundle_output_path_invalid")
        if archive_relative.suffix.casefold() != ".zip":
            return WorkspaceEvidenceBundleResult(status="blocked", reason_code="bundle_archive_must_be_zip")

        sources, warnings = self._collect_sources(root, request)
        if not sources:
            return WorkspaceEvidenceBundleResult(status="blocked", reason_code="bundle_source_evidence_missing", warnings=warnings)
        evidence, phase_rows, evidence_warnings = self._build_evidence(root, sources, request)
        warnings.extend(evidence_warnings)
        summary, reporter_warnings = self._render_summary(request, root, sources, evidence, phase_rows)
        warnings.extend(reporter_warnings)

        agent_session = self.kernel.create_session(
            "aipinho",
            AgentSessionCreateRequest(
                title="AIpinho governed evidence bundle",
                active_workspace_id=workspace.workspace_id,
                metadata_sanitized={"chat_session_id": request.session_id, "operation_id": request.operation_id},
            ),
        )
        run = self.kernel.create_run(
            "aipinho",
            agent_session.session_id,
            AgentRunCreateRequest(
                operation_type="workspace_evidence_bundle",
                status="running",
                workspace_id=workspace.workspace_id,
                capabilities_requested=["read_workspace", "workspace_write", "create_file", "artifact_create", "validation"],
                metadata_sanitized={"chat_session_id": request.session_id, "operation_id": request.operation_id},
            ),
        )

        summary_result = self.gateway.invoke(
            "aipinho",
            run.run_id,
            "create_file",
            ToolInvocationCreateRequest(
                operation_type="create_file",
                workspace_id=workspace.workspace_id,
                path_ref=str(root / summary_relative),
                input={"content": summary.rstrip() + "\n", "overwrite": True, "expected_contains": request.title},
                metadata_sanitized={"execution_mode": request.execution_mode, "operation_id": request.operation_id, "bundle_stage": "summary"},
            ),
        )
        if summary_result.status != "succeeded":
            return self._finish_failed(run.run_id, "bundle_summary_write_failed", summary_result, warnings)

        archive_sources = [str(path.relative_to(root)) for path in sources]
        archive_sources.append(str(summary_relative))
        archive_result = self.gateway.invoke(
            "aipinho",
            run.run_id,
            "create_archive",
            ToolInvocationCreateRequest(
                operation_type="create_archive",
                workspace_id=workspace.workspace_id,
                path_ref=str(root / archive_relative),
                input={
                    "source_paths": list(dict.fromkeys(archive_sources)),
                    "base_path_ref": str(root),
                    "overwrite": True,
                    "skip_missing": True,
                    "max_files": int(self.settings.get("max_archive_files", 20000)),
                    "max_total_bytes": int(self.settings.get("max_archive_bytes", 536870912)),
                },
                metadata_sanitized={"execution_mode": request.execution_mode, "operation_id": request.operation_id, "bundle_stage": "archive"},
            ),
        )
        if archive_result.status != "succeeded":
            return self._finish_failed(run.run_id, "bundle_archive_write_failed", archive_result, warnings)

        validation_status = archive_result.validation_result.status if archive_result.validation_result else None
        final_status = "completed" if validation_status == "passed" else "failed"
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status=final_status,
                validation_status=validation_status,
                artifact_ids=[item.artifact_id for item in archive_result.artifacts],
                metadata_sanitized={
                    "summary_tool_invocation_id": summary_result.tool_invocation.tool_invocation_id,
                    "archive_tool_invocation_id": archive_result.tool_invocation.tool_invocation_id,
                    "operation_id": request.operation_id,
                },
            ),
        )
        artifact = archive_result.artifacts[0] if archive_result.artifacts else None
        return WorkspaceEvidenceBundleResult(
            status="completed" if final_status == "completed" else "failed",
            run_id=run.run_id,
            summary_tool_invocation_id=summary_result.tool_invocation.tool_invocation_id,
            archive_tool_invocation_id=archive_result.tool_invocation.tool_invocation_id,
            summary_path=str(root / summary_relative),
            archive_path=str(root / archive_relative),
            artifact_id=artifact.artifact_id if artifact else None,
            download_endpoint=artifact.download_endpoint if artifact else None,
            validation_status=validation_status,
            entries=[str(item) for item in archive_result.output.get("entries", [])],
            evidence_refs=[
                {"type": "agent_run", "ref_id": run.run_id},
                {"type": "tool_invocation", "ref_id": summary_result.tool_invocation.tool_invocation_id},
                {"type": "tool_invocation", "ref_id": archive_result.tool_invocation.tool_invocation_id},
                *([{"type": "artifact", "ref_id": artifact.artifact_id}] if artifact else []),
            ],
            warnings=list(dict.fromkeys(warnings)),
        )

    def _resolve_workspace(self, workspace_ref: str):
        by_id = self.resolver.resolve(workspace_id=workspace_ref, access="write")
        if by_id.allowed or by_id.reason_code != "workspace_id_not_registered":
            return by_id
        return self.resolver.resolve(path_ref=workspace_ref, access="write")

    def _safe_relative(self, value: str) -> Path | None:
        path = Path(str(value).replace("\\", "/"))
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            return None
        return path

    def _collect_sources(self, root: Path, request: WorkspaceEvidenceBundleRequest) -> tuple[list[Path], list[str]]:
        warnings: list[str] = []
        found: dict[str, Path] = {}
        ignored = {str(item).casefold() for item in self.settings.get("ignored_directories", []) or []}
        max_files = int(self.settings.get("max_source_files", 160))
        for raw in request.source_relative_paths:
            relative = self._safe_relative(raw)
            if relative is None:
                warnings.append(f"source_path_invalid:{raw}")
                continue
            candidate = (root / relative).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                warnings.append(f"source_outside_workspace:{raw}")
                continue
            if candidate.is_file() and not self.secret_guard.is_secret_path(candidate):
                found[str(candidate).casefold()] = candidate
            elif not candidate.exists():
                warnings.append(f"source_missing:{raw}")
        for pattern in request.include_globs:
            relative_pattern = str(pattern).replace("\\", "/").lstrip("/")
            if ".." in Path(relative_pattern).parts:
                warnings.append(f"source_glob_invalid:{pattern}")
                continue
            for candidate in root.glob(relative_pattern):
                if len(found) >= max_files:
                    warnings.append("bundle_source_limit_reached")
                    break
                if not candidate.is_file() or self.secret_guard.is_secret_path(candidate):
                    continue
                try:
                    relative_parts = candidate.relative_to(root).parts
                except ValueError:
                    continue
                if any(part.casefold() in ignored for part in relative_parts[:-1]):
                    continue
                found[str(candidate.resolve()).casefold()] = candidate.resolve()
        return list(found.values())[:max_files], warnings

    def _build_evidence(
        self,
        root: Path,
        sources: list[Path],
        request: WorkspaceEvidenceBundleRequest,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
        evidence: list[dict[str, object]] = []
        warnings: list[str] = []
        allowed = {str(item).casefold() for item in self.settings.get("allowed_text_extensions", []) or []}
        per_file = int(self.settings.get("max_chars_per_file", 12000))
        total_limit = int(self.settings.get("max_total_context_chars", 120000))
        total = 0
        phase_rows: list[dict[str, object]] = []
        for source in sources:
            content = ""
            if source.suffix.casefold() in allowed:
                content = source.read_text(encoding="utf-8", errors="replace")[:per_file]
                content, redaction_warnings = self.secret_guard.redact(content)
                warnings.extend(redaction_warnings)
            relative = source.relative_to(root).as_posix()
            evidence.append({
                "source": relative,
                "size_bytes": source.stat().st_size,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "content": content,
            })
            total += len(content)
            phase_rows.extend(self._phase_rows_from_text(content))
            if total >= total_limit:
                warnings.append("bundle_context_limit_reached")
                break
        system_evidence = self._discover_system_evidence(request.workspace_ref, total_limit - total)
        evidence.extend(system_evidence)
        for item in system_evidence:
            phase_rows.extend(self._phase_rows_from_text(str(item.get("content") or "")))
        return evidence, self._dedupe_phase_rows(phase_rows), warnings

    def _discover_system_evidence(self, workspace_ref: str, remaining_chars: int) -> list[dict[str, object]]:
        if remaining_chars <= 0:
            return []
        candidates: list[Path] = []
        max_reports = int(self.settings.get("max_system_report_files", 12))
        for path in (PATHS.project_root / "reports").rglob("*"):
            if path.is_file() and path.suffix.casefold() in {".md", ".json"}:
                candidates.append(path)
        candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        output: list[dict[str, object]] = []
        consumed = 0
        needle = workspace_ref.casefold()
        for path in candidates:
            if len(output) >= max_reports or consumed >= remaining_chars:
                break
            text = path.read_text(encoding="utf-8", errors="replace")
            if needle not in text.casefold():
                continue
            excerpt, _ = self.secret_guard.redact(text[: min(20000, remaining_chars - consumed)])
            output.append({"source": str(path.relative_to(PATHS.project_root)), "content": excerpt, "system_evidence": True})
            consumed += len(excerpt)
        return output

    def _phase_rows_from_text(self, text: str) -> list[dict[str, object]]:
        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(payload, dict) or not isinstance(payload.get("phases"), list):
            return []
        return [item for item in payload["phases"] if isinstance(item, dict) and "phase" in item and "verdict" in item]

    def _dedupe_phase_rows(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        selected: dict[str, dict[str, object]] = {}
        for row in rows:
            selected[str(row.get("phase"))] = row
        return [selected[key] for key in sorted(selected, key=lambda value: int(value) if value.isdigit() else 999)]

    def _render_summary(
        self,
        request: WorkspaceEvidenceBundleRequest,
        root: Path,
        sources: list[Path],
        evidence: list[dict[str, object]],
        phase_rows: list[dict[str, object]],
    ) -> tuple[str, list[str]]:
        reporter_settings = self.settings.get("reporter", {}) if isinstance(self.settings.get("reporter"), dict) else {}
        warnings: list[str] = []
        if reporter_settings.get("enabled", True):
            binding = self.bindings.resolve_binding("reporter")
            requested_model = binding.primary_model if binding and binding.enabled else None
            role_pass = self.reporter.run(RolePassInput(
                pass_id="workspace_evidence_bundle_reporter",
                role_id="reporter",
                required=True,
                user_message=(
                    "Crie o resumo solicitado usando somente as evidencias sanitizadas. "
                    "Nao invente fases, runs, validacoes ou sucesso. Marque informacao ausente como desconhecida.\n\n"
                    f"Solicitacao original:\n{request.prompt}"
                ),
                purpose="project_report",
                intent_map={"intent_type": "workspace_evidence_bundle", "requires_task": True},
                policy_decision={"read_only_evidence": True, "workspace_write": "tool_gateway_only"},
                file_context_bundle={"workspace": str(root), "files": [str(path.relative_to(root)) for path in sources]},
                evidence=evidence,
                session_id=request.session_id,
                mode="run",
                model_mode="manual_real" if reporter_settings.get("allow_real_inference", True) else "deterministic",
                requested_model_id=requested_model,
                allow_real_inference=bool(reporter_settings.get("allow_real_inference", True)),
                operator_confirmed=True,
                include_trace=True,
            ))
            if role_pass.status == "completed" and role_pass.output and role_pass.output.content.strip():
                content = role_pass.output.content.strip()
                if request.title.casefold() not in content.casefold():
                    content = f"# {request.title}\n\n{content}"
                if role_pass.output.source != "model_evaluated":
                    warnings.append(f"reporter_source:{role_pass.output.source}")
                return content, warnings
            warnings.extend(["reporter_model_unavailable", *role_pass.warnings])
        if not self.settings.get("reporter", {}).get("fallback_to_manifest", True):
            raise RuntimeError("reporter_output_required")
        return self._manifest_summary(request, root, evidence, phase_rows), warnings

    def _manifest_summary(
        self,
        request: WorkspaceEvidenceBundleRequest,
        root: Path,
        evidence: list[dict[str, object]],
        phase_rows: list[dict[str, object]],
    ) -> str:
        lines = [
            f"# {request.title}",
            "",
            f"Data/hora: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            f"Workspace alvo: `{root}`",
            "",
            "## Fases e vereditos conhecidos",
            "",
        ]
        if phase_rows:
            for row in phase_rows:
                lines.append(f"- Fase {row.get('phase')}: `{row.get('verdict')}`")
        else:
            lines.append("- Nenhum contrato estruturado de fases foi localizado; consulte as evidencias abaixo.")
        lines.extend(["", "## Evidencias empacotadas", ""])
        for item in evidence:
            lines.append(f"- `{item.get('source')}` ({item.get('size_bytes', 'system')} bytes)")
        run_ids = sorted(set(re.findall(r"\b(?:agent_run|task_run)_[a-f0-9]+\b", json.dumps(evidence, ensure_ascii=True))))
        lines.extend(["", "## Runs/task IDs conhecidos", ""])
        lines.extend([f"- `{run_id}`" for run_id in run_ids] or ["- Nenhum run ID verificavel foi localizado."])
        validations = sorted(set(re.findall(r"\b(?:passed|failed|no_changes_needed|persistence_real)\b", json.dumps(evidence, ensure_ascii=True), flags=re.IGNORECASE)))
        lines.extend(["", "## Validacoes e estados observados", ""])
        lines.extend([f"- `{item}`" for item in validations] or ["- Nenhum estado de validacao estruturado foi localizado."])
        lines.extend([
            "",
            "## Warnings restantes",
            "",
            "- Resumo produzido por fallback de manifesto porque o reporter model nao entregou saida validada.",
            "",
            "## Veredito sugerido",
            "",
            "`READY_WITH_WARNINGS`",
            "",
            "## Solicitacao original",
            "",
            request.prompt.strip(),
        ])
        return "\n".join(lines)

    def _finish_failed(self, run_id: str, reason_code: str, tool_result, warnings: list[str]) -> WorkspaceEvidenceBundleResult:
        self.kernel.update_run(run_id, AgentRunUpdateRequest(status="failed", error_code=reason_code, metadata_sanitized={"tool_invocation_id": tool_result.tool_invocation.tool_invocation_id}))
        return WorkspaceEvidenceBundleResult(
            status="failed",
            run_id=run_id,
            reason_code=reason_code,
            evidence_refs=[{"type": "tool_invocation", "ref_id": tool_result.tool_invocation.tool_invocation_id}],
            warnings=list(dict.fromkeys([*warnings, tool_result.tool_invocation.block_reason_code or tool_result.tool_invocation.error_code or reason_code])),
        )
