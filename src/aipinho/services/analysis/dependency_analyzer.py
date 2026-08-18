from __future__ import annotations

import fnmatch

from aipinho.schemas.analysis.analysis_finding import AnalysisFinding
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.analysis.project_profile_service import ProjectProfileService


class DependencyAnalyzer:
    def __init__(self, profiles: ProjectProfileService | None = None) -> None:
        self.profiles = profiles or ProjectProfileService()

    def analyze(
        self,
        context: FileContextBundle,
        tree: ProjectTreeSummary | None = None,
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        manifest_patterns = self.profiles.manifest_patterns(tree) if tree else []
        dependency_files = [
            item
            for item in context.items
            if item.status == "included"
            and (
                not manifest_patterns
                or any(fnmatch.fnmatch(item.path, pattern) for pattern in manifest_patterns)
            )
        ]
        for item in dependency_files:
            findings.append(
                AnalysisFinding(
                    finding_id=f"dependency_{item.execution_id or item.path.replace('/', '_')}",
                    category="dependencies",
                    severity="info",
                    title=f"Arquivo de dependencias analisado: {item.path}",
                    summary="O arquivo foi incluido no contexto read-only para orientar diagnostico de stack e validacao futura.",
                    evidence_paths=[item.path],
                    recommendation="Manter dependencias declaradas e testaveis no manifesto oficial do projeto.",
                )
            )
        return findings

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "dependency_analyzer",
            "profile_service": self.profiles.status(),
        }
