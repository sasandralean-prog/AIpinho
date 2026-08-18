from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.analysis.analysis_finding import AnalysisFinding
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary


class ArchitectureAnalyzer:
    def analyze(self, tree: ProjectTreeSummary, context: FileContextBundle, structures: list[str]) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        paths = set(tree.top_level) | set(tree.important_paths) | set(tree.candidate_files)
        findings.append(
            AnalysisFinding(
                finding_id=self._id(),
                category="scope",
                severity="info",
                title="Analise read-only controlada",
                summary="A analise usou somente arvore de projeto e leituras de arquivos permitidos pelo executor read-only.",
                evidence_paths=[item.path for item in context.items if item.status == "included"][:8],
                recommendation="Use o relatorio como diagnostico inicial; mudancas continuam exigindo task, preview e approval.",
            )
        )
        if "config_first_layout" in structures:
            findings.append(self._finding("architecture", "Arquitetura config-first detectada", "O projeto possui config/ como area de contrato configuravel.", [path for path in paths if path.startswith("config/")][:6], "Manter variacoes em config e evitar regras operacionais espalhadas no codigo."))
        else:
            findings.append(self._finding("architecture", "Config central nao evidente", "A arvore analisada nao evidenciou uma area config/ prioritaria.", [], "Se houver variacao operacional, centralize em config versionada antes de crescer servicos."))
        if "services_present" in structures and "schemas_present" in structures:
            findings.append(self._finding("architecture", "Separacao services/schemas detectada", "A estrutura indica separacao entre contratos de dados e logica de dominio.", [path for path in paths if "services/" in path or "schemas/" in path][:8], "Continuar extraindo regras por dominio funcional."))
        if "api_routes_present" in structures:
            findings.append(self._finding("api", "Rotas API separadas detectadas", "A arvore indica routers dedicados para expor contratos HTTP.", [path for path in paths if "api/routers" in path][:8], "Garantir que cada rota tenha schema e teste de contrato."))
        if "tests_present" in structures:
            findings.append(self._finding("validation", "Testes detectados", "A arvore inclui tests/, permitindo regressao automatizada do fluxo read-only.", [path for path in paths if path.startswith("tests/")][:8], "Manter testes positivos e negativos para policies, prompts e side effects."))
        else:
            findings.append(self._finding("validation", "Testes nao detectados no recorte", "O resumo de arvore nao encontrou tests/ no recorte analisado.", [], "Adicionar testes de contrato antes de liberar fluxos operacionais."))
        if context.status in {"partial", "blocked", "degraded"}:
            findings.append(
                AnalysisFinding(
                    finding_id=self._id(),
                    category="limitations",
                    severity="low",
                    title="Contexto parcial",
                    summary="Parte dos arquivos foi omitida ou bloqueada por budget, policy, segredo, binario ou guard de path.",
                    evidence_paths=[item.path for item in context.items],
                    recommendation="Aumente o budget ou informe focus_paths especificos quando precisar de analise mais profunda.",
                )
            )
        return findings

    def _finding(self, category: str, title: str, summary: str, evidence: list[str], recommendation: str) -> AnalysisFinding:
        return AnalysisFinding(finding_id=self._id(), category=category, severity="info", title=title, summary=summary, evidence_paths=evidence, recommendation=recommendation)

    def _id(self) -> str:
        return f"finding_{uuid4().hex}"

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "architecture_analyzer"}
