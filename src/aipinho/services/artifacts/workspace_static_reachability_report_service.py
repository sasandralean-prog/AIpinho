from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.artifacts.workspace_static_reachability_report import (
    WorkspaceStaticReachabilityReportRequest,
    WorkspaceStaticReachabilityReportResult,
)
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver


class WorkspaceStaticReachabilityReportService:
    """Creates a governed report for static/render reachability checks in a workspace."""

    TEXT_EXTENSIONS = {".kt", ".kts", ".java", ".xml", ".gradle", ".md", ".txt", ".json", ".yaml", ".yml"}
    IGNORED_DIRS = {".gradle", ".kotlin", "build", "dist", ".git", "node_modules"}

    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        gateway: AgentToolGatewayService | None = None,
        resolver: AgentToolWorkspaceResolver | None = None,
    ) -> None:
        self.kernel = kernel or AgentSessionKernelService()
        self.gateway = gateway or AgentToolGatewayService(kernel=self.kernel)
        self.resolver = resolver or self.gateway.resolver

    def execute(self, request: WorkspaceStaticReachabilityReportRequest) -> WorkspaceStaticReachabilityReportResult:
        workspace = self._resolve_workspace(request.workspace_ref)
        if not workspace.allowed or not workspace.root_path_sanitized:
            return WorkspaceStaticReachabilityReportResult(status="blocked", reason_code=workspace.reason_code)
        root = Path(workspace.resolved_path_sanitized or workspace.root_path_sanitized).resolve()
        report_relative = self._safe_relative(request.report_relative_path)
        if report_relative is None or report_relative.suffix.casefold() not in {".md", ".txt"}:
            return WorkspaceStaticReachabilityReportResult(status="blocked", reason_code="static_report_output_path_invalid")
        expected = request.expected_text.strip()
        if not expected:
            return WorkspaceStaticReachabilityReportResult(status="blocked", reason_code="expected_text_required")

        matched_files = self._find_text(root, expected)
        status_label = "render_qa_passed_with_warning" if matched_files else "visual_qa_failed"
        report = self._render_report(request, root, matched_files, status_label)

        agent_session = self.kernel.create_session(
            "aipinho",
            AgentSessionCreateRequest(
                title="AIpinho static reachability QA",
                active_workspace_id=workspace.workspace_id,
                metadata_sanitized={"chat_session_id": request.session_id, "operation_id": request.operation_id},
            ),
        )
        run = self.kernel.create_run(
            "aipinho",
            agent_session.session_id,
            AgentRunCreateRequest(
                operation_type="workspace_static_reachability_report",
                status="running",
                workspace_id=workspace.workspace_id,
                capabilities_requested=["read_workspace", "workspace_write", "create_file", "validation"],
                metadata_sanitized={"chat_session_id": request.session_id, "operation_id": request.operation_id},
            ),
        )
        result = self.gateway.invoke(
            "aipinho",
            run.run_id,
            "create_file",
            ToolInvocationCreateRequest(
                operation_type="create_file",
                workspace_id=workspace.workspace_id,
                path_ref=str(root / report_relative),
                input={"content": report.rstrip() + "\n", "overwrite": True, "expected_contains": status_label},
                metadata_sanitized={"execution_mode": request.execution_mode, "operation_id": request.operation_id, "qa_stage": "static_reachability"},
            ),
        )
        if result.status != "succeeded":
            self.kernel.update_run(run.run_id, AgentRunUpdateRequest(status="failed", error_code=result.tool_invocation.block_reason_code or result.tool_invocation.error_code))
            return WorkspaceStaticReachabilityReportResult(
                status="failed",
                run_id=run.run_id,
                reason_code=result.tool_invocation.block_reason_code or result.tool_invocation.error_code or "static_report_write_failed",
                warnings=[result.tool_invocation.output_summary_sanitized or "static_report_write_failed"],
                evidence_refs=[{"type": "tool_invocation", "ref_id": result.tool_invocation.tool_invocation_id}],
            )
        validation_status = result.validation_result.status if result.validation_result else None
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status="completed" if matched_files else "completed_with_warnings",
                validation_status=validation_status,
                metadata_sanitized={"operation_id": request.operation_id, "report_tool_invocation_id": result.tool_invocation.tool_invocation_id},
            ),
        )
        return WorkspaceStaticReachabilityReportResult(
            status="completed" if matched_files else "completed_with_warnings",
            run_id=run.run_id,
            report_tool_invocation_id=result.tool_invocation.tool_invocation_id,
            report_path=str(root / report_relative),
            validation_status=validation_status,
            matched_files=[item.relative_to(root).as_posix() for item in matched_files],
            warnings=["visual_screenshot_unavailable", "static_reachability_used_instead_of_visual_screenshot"],
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

    def _find_text(self, root: Path, expected: str) -> list[Path]:
        matches: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.casefold() not in self.TEXT_EXTENSIONS:
                continue
            if any(part in self.IGNORED_DIRS for part in path.relative_to(root).parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if expected in text:
                matches.append(path)
        return matches

    def _render_report(
        self,
        request: WorkspaceStaticReachabilityReportRequest,
        root: Path,
        matched_files: list[Path],
        status_label: str,
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        relative_matches = [item.relative_to(root).as_posix() for item in matched_files]
        lines = [
            "# AIpinho Firetest Visual/Render QA",
            "",
            f"- Data/hora UTC: `{now}`",
            f"- Workspace: `{root}`",
            "- Metodo usado: static reachability + filesystem validation.",
            "- Screenshot: nao.",
            "- Limitacao: visual_screenshot_unavailable.",
            f"- Texto esperado: `{request.expected_text}`",
            "",
            "## Resultado",
            "",
            f"- Veredito: `{status_label}`",
            "- O texto foi encontrado em fonte de UI alcançavel." if matched_files else "- O texto nao foi encontrado nos arquivos textuais verificados.",
            "",
            "## Arquivos verificados com match",
            "",
        ]
        lines.extend([f"- `{item}`" for item in relative_matches] or ["- Nenhum match encontrado."])
        lines.extend([
            "",
            "## Comandos executados",
            "",
            "- Varredura estatica de arquivos textuais do workspace.",
            "- Escrita governada deste relatorio via Tool Gateway `create_file`.",
            "",
            "## Solicitacao original",
            "",
            request.prompt.strip(),
        ])
        return "\n".join(lines)
