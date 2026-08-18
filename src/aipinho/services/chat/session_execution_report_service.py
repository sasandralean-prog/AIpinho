from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.interaction.interaction_core import ChatMessageService
from aipinho.services.patching.apply.patch_apply_service import PatchApplyService
from aipinho.services.patching.patch_plan_store import PatchPlanStore


class SessionExecutionReportService:
    """Builds a grounded read-only report from session execution records."""

    def __init__(
        self,
        message_service: ChatMessageService | None = None,
        patch_apply_service: PatchApplyService | None = None,
        plan_store: PatchPlanStore | None = None,
    ) -> None:
        self.message_service = message_service or ChatMessageService()
        self.patch_apply_service = patch_apply_service or PatchApplyService()
        self.plan_store = plan_store or PatchPlanStore()

    def report(self, session_id: str, decision: ChatOperationDecision) -> ChatResponse:
        messages = self.message_service.list(session_id=session_id, limit=1000)
        plan_ids = self._session_plan_ids(messages)
        plan_reports = [self._plan_report(plan_id) for plan_id in plan_ids]
        completed_runs = [run for plan in plan_reports for run in plan["runs"] if run.get("result_status") == "completed"]
        failed_runs = [run for plan in plan_reports for run in plan["runs"] if str(run.get("result_status") or "").startswith("failed")]
        changed_files = self._changed_files(completed_runs)
        build_evidence = self._build_evidence(plan_reports)
        read_only_sources = sorted({str(plan.get("source_id") or "") for plan in plan_reports if plan.get("source_id")})
        changed_file_lines = (
            [f"- {file_path}" for file_path in changed_files]
            if changed_files
            else ["- Nenhum arquivo alterado com sucesso foi encontrado nos registros."]
        )

        status = "ok" if completed_runs else "degraded"
        response_warnings = ["session_has_failed_or_rolled_back_apply_runs"] if failed_runs else []
        lines = [
            "Relatorio final da execucao supervisionada",
            "",
            f"Status: {status}.",
            f"Sessao: {session_id}.",
            "",
            "Resumo:",
            self._summary(plan_reports, completed_runs, failed_runs, changed_files, build_evidence),
            "",
            "Evidencias de fluxo:",
            f"- Planos de patch encontrados: {len(plan_reports)}.",
            f"- Apply runs concluidos: {len(completed_runs)}.",
            f"- Apply runs com falha/rollback: {len(failed_runs)}.",
            f"- Fonte read-only referenciada: {', '.join(read_only_sources) if read_only_sources else 'nao encontrada nos registros da sessao'}.",
            "",
            "Arquivos criados ou corrigidos:",
            *changed_file_lines,
            "",
            "Riscos e problemas observados:",
            *self._risk_lines(plan_reports, failed_runs),
            "",
            "Validacao:",
            f"- Post-apply validation: {'passou' if completed_runs else 'nao ha apply concluido validado'}.",
            f"- Build/artifacts detectados: {build_evidence or 'nao detectado nos workspaces registrados'}.",
            "",
            "Proximos passos:",
            "- Abrir o projeto alvo e fazer QA funcional manual.",
            "- Manter o projeto legado como fonte somente leitura.",
            "- Se novos requisitos aparecerem, gerar novo preview governado antes de qualquer escrita.",
        ]
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status=status,
            message="\n".join(lines),
            intent={
                "intent_type": "session_execution_report",
                "requires_task": False,
                "requires_workspace": False,
                "plan_count": len(plan_reports),
                "completed_apply_runs": len(completed_runs),
                "failed_apply_runs": len(failed_runs),
            },
            policy={"approval_required_for": [], "read_only": True, "executes_tools": False},
            message_type="assistant_final_answer",
            operation_type="session_execution_report",
            operation_id=decision.operation_id,
            evidence_refs=[
                *[{"type": "patch_plan", "ref_id": str(plan["plan_id"])} for plan in plan_reports],
                *[
                    {"type": "patch_apply_run", "ref_id": str(run["apply_run_id"])}
                    for plan in plan_reports
                    for run in plan["runs"]
                ],
            ],
            is_final_answer=True,
            grounded=True,
            grounding_required=False,
            warnings=response_warnings,
            result_ref_id=f"result_{decision.operation_id}",
        )

    def _session_plan_ids(self, messages: list[Any]) -> list[str]:
        plan_ids: list[str] = []
        for message in messages:
            metadata = getattr(message, "metadata", {}) or {}
            for key in ("preview_id", "task_preview_id"):
                value = str(metadata.get(key) or "")
                if value.startswith("patch_plan_"):
                    plan_ids.append(value)
        return list(dict.fromkeys(plan_ids))

    def _plan_report(self, plan_id: str) -> dict[str, Any]:
        plan = self.plan_store.get_plan(plan_id)
        runs = []
        for run in self.patch_apply_service.list_runs(plan_id=plan_id, limit=20):
            result = self.patch_apply_service.get_result(run.apply_run_id)
            runs.append(
                {
                    "apply_run_id": run.apply_run_id,
                    "run_status": run.status,
                    "result_status": result.status if result else None,
                    "safe_to_report_success": result.safe_to_report_success if result else False,
                    "files": [file.model_dump() for file in result.files] if result else [],
                    "validation_passed": result.post_apply_validation.passed if result else False,
                    "blocking_reasons": result.post_apply_validation.blocking_reasons if result else [],
                }
            )
        return {
            "plan_id": plan_id,
            "status": plan.status if plan else "missing",
            "workspace": plan.workspace if plan else "",
            "source_id": plan.source_id if plan else "",
            "quality_status": (plan.quality_gate or {}).get("status") if plan else None,
            "blocked_reasons": plan.blocked_reasons if plan else ["plan_missing"],
            "runs": runs,
        }

    def _changed_files(self, completed_runs: list[dict[str, Any]]) -> list[str]:
        files: list[str] = []
        for run in completed_runs:
            for file in run.get("files", []):
                if file.get("changed") is True:
                    files.append(str(file.get("file_path") or ""))
        return sorted(dict.fromkeys(file for file in files if file))

    def _build_evidence(self, plan_reports: list[dict[str, Any]]) -> str:
        workspaces = sorted({str(plan.get("workspace") or "") for plan in plan_reports if plan.get("workspace")})
        evidence: list[str] = []
        for workspace in workspaces:
            root = Path(workspace)
            classes_dir = root / "build" / "classes"
            if classes_dir.exists():
                evidence.append(f"build/classes presente em {workspace}")
        return "; ".join(evidence)

    def _summary(
        self,
        plan_reports: list[dict[str, Any]],
        completed_runs: list[dict[str, Any]],
        failed_runs: list[dict[str, Any]],
        changed_files: list[str],
        build_evidence: str,
    ) -> str:
        if completed_runs:
            return (
                f"A sessao criou ou corrigiu {len(changed_files)} arquivo(s) por patch governado, "
                f"com {len(failed_runs)} tentativa(s) falha(s)/rollback registradas e validacao final positiva. "
                f"{'Ha evidencia de build gerado.' if build_evidence else 'Nao encontrei evidencia de build no registro consultado.'}"
            )
        if plan_reports:
            return "Ha previews registrados, mas nao encontrei apply concluido com sucesso nesta sessao."
        return "Nao encontrei previews ou apply runs suficientes para relatorio final fundamentado."

    def _risk_lines(self, plan_reports: list[dict[str, Any]], failed_runs: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []
        for plan in plan_reports:
            if plan.get("blocked_reasons"):
                lines.append(f"- Plano {plan['plan_id']} registrou bloqueios: {', '.join(plan['blocked_reasons'])}.")
        for run in failed_runs:
            reasons = run.get("blocking_reasons") or ["falha sem motivo estruturado"]
            lines.append(f"- Apply run {run['apply_run_id']} falhou/rollback: {', '.join(reasons)}.")
        if not lines:
            lines.append("- Nenhum bloqueio final encontrado nos registros consultados.")
        return lines
