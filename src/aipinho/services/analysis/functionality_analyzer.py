from __future__ import annotations

import re
import unicodedata
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.analysis_finding import AnalysisFinding
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.utils.yaml_loader import load_yaml_file


class FunctionalityAnalyzer:
    _README_NAMES = {"readme.md", "readme.txt", "readme"}
    _UI_LITERAL_PATTERNS = (
        re.compile(r'\b(?:Text|Button|Label|MenuItem)\s*\(\s*"([^"\r\n]{2,80})"'),
        re.compile(r'\b(?:title|label|placeholder|heading)\s*=\s*"([^"\r\n]{2,80})"'),
    )

    def __init__(self, policy: dict[str, object] | None = None) -> None:
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "analysis" / "project_analysis_policy.yaml",
            critical=True,
            root=PATHS.config_root / "analysis",
        )

    def analyze(self, context: FileContextBundle) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        readme_finding = self._readme_purpose(context)
        if readme_finding:
            findings.append(readme_finding)
        surface_finding = self._user_facing_surfaces(context)
        if surface_finding:
            findings.append(surface_finding)
        module_finding = self._source_modules(context)
        if module_finding:
            findings.append(module_finding)
        findings.extend(self._semantic_code_evidence(context))
        return findings

    def _readme_purpose(self, context: FileContextBundle) -> AnalysisFinding | None:
        for item in context.items:
            if item.status != "included" or not item.content:
                continue
            if item.path.replace("\\", "/").split("/")[-1].lower() not in self._README_NAMES:
                continue
            paragraph = self._first_descriptive_paragraph(item.content)
            if not paragraph:
                continue
            return AnalysisFinding(
                finding_id=f"functionality_{uuid4().hex}",
                category="functionality",
                severity="info",
                title="Finalidade declarada do projeto",
                summary=paragraph,
                evidence_paths=[item.path],
                recommendation="Validar esta finalidade contra os modulos e fluxos observados no codigo.",
            )
        return None

    def _user_facing_surfaces(self, context: FileContextBundle) -> AnalysisFinding | None:
        labels: list[str] = []
        evidence: list[str] = []
        for item in context.items:
            if item.status != "included" or not item.content:
                continue
            matched = False
            for pattern in self._UI_LITERAL_PATTERNS:
                for value in pattern.findall(item.content):
                    normalized = " ".join(value.split()).strip()
                    if self._useful_label(normalized) and normalized not in labels:
                        labels.append(normalized)
                        matched = True
            if matched:
                evidence.append(item.path)
        if not labels:
            return None
        visible = labels[:16]
        suffix = f" e mais {len(labels) - len(visible)}" if len(labels) > len(visible) else ""
        return AnalysisFinding(
            finding_id=f"functionality_{uuid4().hex}",
            category="functionality",
            severity="info",
            title="Superficies funcionais observadas",
            summary=f"Elementos de interface observados: {', '.join(visible)}{suffix}.",
            evidence_paths=evidence[:8],
            recommendation="Confirmar estes fluxos em teste de interface antes de tratar a lista como cobertura completa.",
        )

    def _source_modules(self, context: FileContextBundle) -> AnalysisFinding | None:
        source_paths = [
            item.path
            for item in context.items
            if item.status == "included"
            and item.path.replace("\\", "/").startswith(("src/", "app/", "lib/"))
        ]
        if not source_paths:
            return None
        modules = [path.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0] for path in source_paths]
        return AnalysisFinding(
            finding_id=f"functionality_{uuid4().hex}",
            category="functionality",
            severity="info",
            title="Modulos de implementacao observados",
            summary=f"Modulos lidos no recorte: {', '.join(list(dict.fromkeys(modules))[:20])}.",
            evidence_paths=source_paths[:12],
            recommendation="Use os modulos citados como evidencia do recorte, nao como inventario completo do projeto.",
        )

    def _semantic_code_evidence(self, context: FileContextBundle) -> list[AnalysisFinding]:
        groups = self._semantic_groups()
        if not groups:
            return []
        grouped_paths: dict[str, list[str]] = {name: [] for name in groups}
        grouped_terms: dict[str, list[str]] = {name: [] for name in groups}
        grouped_symbols: dict[str, list[str]] = {name: [] for name in groups}
        for item in context.items:
            if item.status != "included" or not item.content:
                continue
            searchable = self._normalize(f"{item.path}\n{item.content}")
            symbols = self._symbols(item.content)
            for group_name, terms in groups.items():
                hits = [term for term in terms if self._term_present(searchable, term)]
                if not hits:
                    continue
                if item.path not in grouped_paths[group_name]:
                    grouped_paths[group_name].append(item.path)
                for term in hits:
                    if term not in grouped_terms[group_name]:
                        grouped_terms[group_name].append(term)
                for symbol in symbols:
                    if symbol not in grouped_symbols[group_name]:
                        grouped_symbols[group_name].append(symbol)
        findings: list[AnalysisFinding] = []
        for group_name, paths in grouped_paths.items():
            if not paths:
                continue
            terms = grouped_terms[group_name][:12]
            symbols = grouped_symbols[group_name][:12]
            symbol_fragment = f" Symbols: {', '.join(symbols)}." if symbols else ""
            findings.append(
                AnalysisFinding(
                    finding_id=f"semantic_evidence_{uuid4().hex}",
                    category="semantic_code_evidence",
                    severity="info",
                    title=f"Evidencia semantica observada: {group_name}",
                    summary=(
                        f"Sinais de {group_name} encontrados no recorte analisado. "
                        f"Termos: {', '.join(terms)}.{symbol_fragment} "
                        f"Arquivos relacionados: {', '.join(paths[:8])}."
                    ),
                    evidence_paths=paths[:12],
                    recommendation=(
                        "Usar esta evidencia como ponto de partida para analise especializada; "
                        "confirmar comportamento com validacao apropriada antes de declarar causa raiz."
                    ),
                )
            )
        return findings

    def _semantic_groups(self) -> dict[str, list[str]]:
        root = self.policy.get("project_analysis", {}) if isinstance(self.policy, dict) else {}
        value = root.get("semantic_evidence_groups", {}) if isinstance(root, dict) else {}
        if not isinstance(value, dict):
            return {}
        return {
            str(name): [self._normalize(str(term)) for term in terms or [] if str(term).strip()]
            for name, terms in value.items()
            if isinstance(terms, list)
        }

    def _symbols(self, content: str) -> list[str]:
        patterns = (
            re.compile(r"\bfun\s+([A-Za-z_][A-Za-z0-9_]*)"),
            re.compile(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)"),
            re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)"),
            re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"),
            re.compile(r"\b(?:public|private|protected|internal)?\s*(?:suspend\s+)?[A-Za-z_][A-Za-z0-9_<>,.?]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        )
        symbols: list[str] = []
        for pattern in patterns:
            for match in pattern.findall(content or ""):
                if match not in symbols:
                    symbols.append(match)
        return symbols[:24]

    def _first_descriptive_paragraph(self, content: str) -> str:
        paragraphs = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))
        for paragraph in paragraphs:
            normalized = " ".join(line.strip() for line in paragraph.splitlines() if not line.lstrip().startswith("#"))
            normalized = normalized.strip()
            if len(normalized) >= 24 and not normalized.startswith("```"):
                return normalized[:600]
        return ""

    def _useful_label(self, value: str) -> bool:
        if len(value) < 2 or len(value) > 80:
            return False
        if value.startswith(("/", "http://", "https://")):
            return False
        return any(char.isalpha() for char in value)

    def _normalize(self, value: str) -> str:
        expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value or ""))
        normalized = unicodedata.normalize("NFKD", expanded).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-zA-Z0-9_]+", " ", normalized.casefold()).strip()

    def _term_present(self, text: str, term: str) -> bool:
        if not term:
            return False
        return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text))

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "functionality_analyzer",
            "read_only": True,
            "model_required": False,
        }
