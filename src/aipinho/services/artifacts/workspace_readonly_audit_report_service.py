from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.artifacts.workspace_readonly_audit_report import (
    WorkspaceReadonlyAuditReportRequest,
    WorkspaceReadonlyAuditReportResult,
)
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class WorkspaceReadonlyAuditReportService:
    """Creates a governed report for read-only code/config/test audits."""

    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        gateway: AgentToolGatewayService | None = None,
        resolver: AgentToolWorkspaceResolver | None = None,
        policy: dict[str, Any] | None = None,
    ) -> None:
        self.kernel = kernel or AgentSessionKernelService()
        self.gateway = gateway or AgentToolGatewayService(kernel=self.kernel)
        self.resolver = resolver or self.gateway.resolver
        self.secret_guard = SecretGuardService()
        self.local_planner = AgentLocalActionPlanner()
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "artifacts" / "workspace_readonly_audit_policy.yaml",
            critical=True,
            root=PATHS.config_root / "artifacts",
        )

    @property
    def settings(self) -> dict[str, Any]:
        value = self.policy.get("workspace_readonly_audit", {})
        return value if isinstance(value, dict) else {}

    def execute(self, request: WorkspaceReadonlyAuditReportRequest) -> WorkspaceReadonlyAuditReportResult:
        if not self.settings.get("enabled", True):
            return WorkspaceReadonlyAuditReportResult(status="blocked", reason_code="workspace_readonly_audit_disabled")
        workspace = self._resolve_workspace(request.workspace_ref)
        if not workspace.allowed or not workspace.root_path_sanitized:
            return WorkspaceReadonlyAuditReportResult(status="blocked", reason_code=workspace.reason_code)
        root = Path(workspace.resolved_path_sanitized or workspace.root_path_sanitized).resolve()
        report_relative = self._safe_relative(request.report_relative_path)
        if report_relative is None or report_relative.suffix.casefold() not in {".md", ".txt"}:
            return WorkspaceReadonlyAuditReportResult(status="blocked", reason_code="audit_report_output_path_invalid")
        terms = self._clean_terms(request.search_terms)
        if not terms:
            return WorkspaceReadonlyAuditReportResult(status="blocked", reason_code="audit_search_terms_required")

        report_path = root / report_relative
        if report_path.exists():
            strategy = str(self.settings.get("existing_report_strategy") or "read_existing")
            if strategy == "ask_before_overwrite":
                return WorkspaceReadonlyAuditReportResult(
                    status="blocked",
                    reason_code="audit_report_exists_requires_overwrite_approval",
                    report_path=str(report_path),
                    warnings=["existing_report_requires_approval"],
                    evidence_refs=[{"type": "report_file", "ref_id": str(report_path)}],
                )
            if strategy == "create_timestamped_copy":
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                report_relative = report_relative.with_name(f"{report_relative.stem}_{timestamp}{report_relative.suffix}")
                report_path = root / report_relative
            else:
                return WorkspaceReadonlyAuditReportResult(
                    status="completed",
                    reason_code="existing_report_reused",
                    report_path=str(report_path),
                    validation_status="existing_report_reused",
                    warnings=["existing_report_reused", "report_write_idempotent"],
                    evidence_refs=[{"type": "report_file", "ref_id": str(report_path)}],
                )
        if report_path.exists():
            return WorkspaceReadonlyAuditReportResult(
                status="blocked",
                reason_code="audit_report_timestamped_copy_collision",
                report_path=str(report_path),
                warnings=["timestamped_report_already_exists"],
                evidence_refs=[{"type": "report_file", "ref_id": str(report_path)}],
            )

        matches = self._scan(root, terms)
        workspace_summary = self.local_planner.workspace_summary(str(root))
        report = self._render_report(request, root, terms, matches, workspace_summary)

        agent_session = self.kernel.create_session(
            "aipinho",
            AgentSessionCreateRequest(
                title="AIpinho read-only workspace audit",
                active_workspace_id=workspace.workspace_id,
                metadata_sanitized={"chat_session_id": request.session_id, "operation_id": request.operation_id},
            ),
        )
        run = self.kernel.create_run(
            "aipinho",
            agent_session.session_id,
            AgentRunCreateRequest(
                operation_type="workspace_readonly_audit_report",
                status="running",
                workspace_id=workspace.workspace_id,
                capabilities_requested=["read_workspace", "workspace_write", "create_file", "validation"],
                metadata_sanitized={"chat_session_id": request.session_id, "operation_id": request.operation_id, "audit_terms": terms},
            ),
        )
        result = self.gateway.invoke(
            "aipinho",
            run.run_id,
            "create_file",
            ToolInvocationCreateRequest(
                operation_type="workspace_readonly_audit_report",
                workspace_id=workspace.workspace_id,
                path_ref=str(report_path),
                input={"content": report.rstrip() + "\n", "overwrite": True, "expected_contains": "workspace_readonly_audit"},
                metadata_sanitized={"execution_mode": request.execution_mode, "operation_id": request.operation_id, "audit_stage": "report"},
            ),
        )
        if result.status != "succeeded":
            self.kernel.update_run(run.run_id, AgentRunUpdateRequest(status="failed", error_code=result.tool_invocation.block_reason_code or result.tool_invocation.error_code))
            return WorkspaceReadonlyAuditReportResult(
                status="failed",
                run_id=run.run_id,
                reason_code=result.tool_invocation.block_reason_code or result.tool_invocation.error_code or "audit_report_write_failed",
                warnings=[result.tool_invocation.output_summary_sanitized or "audit_report_write_failed"],
                evidence_refs=[{"type": "tool_invocation", "ref_id": result.tool_invocation.tool_invocation_id}],
            )

        validation_status = result.validation_result.status if result.validation_result else None
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status="completed",
                validation_status=validation_status,
                metadata_sanitized={"operation_id": request.operation_id, "report_tool_invocation_id": result.tool_invocation.tool_invocation_id},
            ),
        )
        matched_files = sorted({str(item["path"]) for item in matches})
        return WorkspaceReadonlyAuditReportResult(
            status="completed",
            run_id=run.run_id,
            report_tool_invocation_id=result.tool_invocation.tool_invocation_id,
            report_path=str(report_path),
            validation_status=validation_status,
            matched_files=matched_files,
            match_count=len(matches),
            evidence_refs=[
                {"type": "agent_run", "ref_id": run.run_id},
                {"type": "tool_invocation", "ref_id": result.tool_invocation.tool_invocation_id},
            ],
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

    def _clean_terms(self, terms: list[str]) -> list[str]:
        stop_words = {str(item).casefold() for item in self.settings.get("generic_stop_words", []) or []}
        cleaned: list[str] = []
        for raw in terms:
            term = str(raw).strip().strip("`'\".,;:()[]{}")
            if len(term) < 3 or term.casefold() in stop_words:
                continue
            if term not in cleaned:
                cleaned.append(term)
        return cleaned[: int(self.settings.get("max_terms", 24))]

    def _scan(self, root: Path, terms: list[str]) -> list[dict[str, object]]:
        allowed = {str(item).casefold() for item in self.settings.get("allowed_text_extensions", []) or []}
        ignored = {str(item).casefold() for item in self.settings.get("ignored_directories", []) or []}
        max_files = int(self.settings.get("max_files", 240))
        max_matches = int(self.settings.get("max_matches", 80))
        max_excerpt_chars = int(self.settings.get("max_excerpt_chars", 220))
        matches: list[dict[str, object]] = []
        scanned = 0
        for path in root.rglob("*"):
            if scanned >= max_files or len(matches) >= max_matches:
                break
            if not path.is_file() or path.suffix.casefold() not in allowed:
                continue
            try:
                relative_parts = path.relative_to(root).parts
            except ValueError:
                continue
            if any(part.casefold() in ignored for part in relative_parts[:-1]):
                continue
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lowered = text.casefold()
            matched_terms = [term for term in terms if term.casefold() in lowered]
            if not matched_terms:
                continue
            line_no, excerpt = self._first_excerpt(text, matched_terms[0], max_excerpt_chars)
            excerpt, redaction_warnings = self.secret_guard.redact(excerpt)
            matches.append({
                "path": path.relative_to(root).as_posix(),
                "line": line_no,
                "terms": matched_terms,
                "excerpt": excerpt,
                "redaction_warnings": redaction_warnings,
            })
        return matches

    def _first_excerpt(self, text: str, term: str, max_chars: int) -> tuple[int, str]:
        lowered = text.casefold()
        idx = lowered.find(term.casefold())
        if idx < 0:
            return 1, ""
        line_no = text[:idx].count("\n") + 1
        start = max(0, idx - max_chars // 2)
        end = min(len(text), idx + len(term) + max_chars // 2)
        excerpt = text[start:end].replace("\r", " ").replace("\n", " ")
        return line_no, excerpt.strip()

    def _render_report(
        self,
        request: WorkspaceReadonlyAuditReportRequest,
        root: Path,
        terms: list[str],
        matches: list[dict[str, object]],
        workspace_summary: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        operational_section = self._render_operational_section(request, workspace_summary)
        lines = [
            "# AIpinho Workspace Read-only Audit",
            "",
            f"- Tipo: `workspace_readonly_audit`",
            f"- Data/hora UTC: `{now}`",
            f"- Workspace: `{root}`",
            "- Metodo: varredura textual read-only + escrita governada do relatorio.",
            "- Side effects no workspace: apenas este relatorio em caminho solicitado.",
            "",
            "## Termos de busca",
            "",
        ]
        lines.extend([f"- `{term}`" for term in terms])
        if operational_section:
            lines.extend(["", "## Sintese operacional", "", operational_section.rstrip()])
        lines.extend(["", "## Arquivos candidatos encontrados", ""])
        if not matches:
            lines.append("- Nenhum match encontrado nos arquivos textuais varridos.")
        for item in matches:
            lines.append(f"- `{item['path']}` linha {item['line']} termos: {', '.join(str(term) for term in item['terms'])}")
            if item.get("excerpt"):
                lines.append(f"  - Excerpt sanitizado: {item['excerpt']}")
        lines.extend([
            "",
            "## Recomendacao segura",
            "",
            "- Use este relatorio como indice de auditoria; qualquer alteracao deve passar por task/patch/approval/validation.",
            "- Evite expectativas fixas por projeto/path/modelo. Prefira policy ativa, perfil de teste explicito e fixtures parametrizadas.",
            "",
            "## Solicitacao original",
            "",
            request.prompt.strip(),
        ])
        return "\n".join(lines)

    def _render_operational_section(
        self,
        request: WorkspaceReadonlyAuditReportRequest,
        workspace_summary: dict[str, Any] | None,
    ) -> str:
        if not workspace_summary:
            return ""
        report = self.local_planner.report_from_workspace_summary(request.prompt, workspace_summary).strip()
        return report
