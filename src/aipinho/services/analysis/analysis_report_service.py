from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.analysis.analysis_finding import AnalysisFinding
from aipinho.schemas.analysis.analysis_report import AnalysisReport
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary


class AnalysisReportService:
    def build_report(self, request: ProjectAnalysisRequest, tree: ProjectTreeSummary, context: FileContextBundle, structures: list[str], findings: list[AnalysisFinding]) -> AnalysisReport:
        limitations: list[str] = []
        if tree.status != "ok":
            limitations.append(f"project_tree_status:{tree.status}")
        if context.status != "ok":
            limitations.append(f"file_context_status:{context.status}")
        if context.omitted_files:
            limitations.append("some_files_omitted_by_budget_or_policy")
        summary = self._summary(tree, context, structures)
        sections = [
            {"title": "Escopo", "content": "Analise read-only sem escrita, patch, shell mutavel, memoria persistente, RAG ou chamada LLM."},
            {"title": "Estruturas detectadas", "items": structures},
            {"title": "Arquivos lidos", "items": [item.path for item in context.items if item.status == "included"]},
            {"title": "Arquivos omitidos/bloqueados", "items": [item.path for item in context.omitted_files] + tree.blocked_paths},
        ]
        status = "ok"
        if context.status in {"blocked", "invalid"} or tree.status in {"blocked", "invalid"}:
            status = "blocked" if "blocked" in {context.status, tree.status} else "invalid"
        elif limitations:
            status = "partial"
        return AnalysisReport(
            report_id=f"analysis_report_{uuid4().hex}",
            status=status,
            title="Read-only project analysis report",
            summary=summary,
            sections=sections,
            findings=findings,
            limitations=limitations,
            warnings=list(dict.fromkeys([*tree.warnings, *context.warnings])),
        )

    def _summary(self, tree: ProjectTreeSummary, context: FileContextBundle, structures: list[str]) -> str:
        included = len([item for item in context.items if item.status == "included"])
        detected = ", ".join(structures) if structures else "nenhuma estrutura forte detectada no recorte"
        return f"Projeto analisado em modo read-only: {tree.total_files_seen} arquivos vistos, {included} arquivos pequenos lidos e estruturas detectadas: {detected}."

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "analysis_report"}
