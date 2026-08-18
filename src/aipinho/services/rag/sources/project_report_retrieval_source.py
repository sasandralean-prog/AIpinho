from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest
from aipinho.services.rag.citation_builder import CitationBuilder


class ProjectReportRetrievalSource:
    source_id = "project_reports"

    def __init__(self, citations: CitationBuilder | None = None) -> None:
        self.citations = citations or CitationBuilder()

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalHit]:
        roots = [PATHS.project_root / "reports", PATHS.project_root / "reports" / "sprints"]
        candidates: list[Path] = []
        if request.report_id:
            candidates.extend((PATHS.project_root / "reports").rglob(f"*{request.report_id}*.md"))
        for root in roots:
            if root.exists():
                candidates.extend(root.glob("*.md"))
        hits: list[RetrievalHit] = []
        seen: set[Path] = set()
        for path in candidates:
            if path in seen or not path.exists() or path.suffix.lower() != ".md":
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8", errors="ignore")
            hits.extend(self._hits_from_report(path, text, request))
            if len(hits) >= request.budget.max_hits_per_source:
                break
        return hits[: request.budget.max_hits_per_source]

    def _hits_from_report(self, path: Path, text: str, request: RetrievalRequest) -> list[RetrievalHit]:
        tokens = set(request.query.lower().split())
        hits: list[RetrievalHit] = []
        section = "report"
        for index, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                section = stripped.strip("# ").strip() or section
            if not stripped:
                continue
            if tokens and not any(token in stripped.lower() for token in tokens):
                continue
            rel = str(path.relative_to(PATHS.project_root))
            excerpt = stripped[: request.budget.max_hit_excerpt_chars]
            citation = self.citations.build(citation_type="report_section", source_id=self.source_id, source_type="project_report", ref=rel, location=f"{rel}:{index}", line_start=index, line_end=index, section=section, excerpt=excerpt)
            hits.append(RetrievalHit(source_id=self.source_id, source_type="project_report", title=path.stem, excerpt=excerpt, citation=citation, source_ref=citation.source_ref, metadata={"report_path": rel, "section": section}))
            if len(hits) >= request.budget.max_hits_per_source:
                break
        return hits

    def status(self) -> dict[str, object]:
        return {"status": "ok", "source": self.source_id, "read_only": True}
