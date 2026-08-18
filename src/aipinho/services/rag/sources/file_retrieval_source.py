from __future__ import annotations

from pathlib import Path

from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.rag.citation_builder import CitationBuilder
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService


class FileRetrievalSource:
    source_id = "project_files"

    def __init__(self, read_only: ReadOnlyExecutionService | None = None, citations: CitationBuilder | None = None) -> None:
        self.read_only = read_only or ReadOnlyExecutionService()
        self.citations = citations or CitationBuilder()

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalHit]:
        workspace = request.workspace or request.scope.workspace
        if not workspace:
            return []
        hits: list[RetrievalHit] = []
        for path in request.paths[: request.budget.max_files_read]:
            result = self.read_only.execute(ToolExecutionRequest(tool_id="filesystem.read_file", input={"workspace": workspace, "path": path}, include_content=True))
            if result.status != "executed_readonly" or not result.content:
                continue
            hits.extend(self._hits_from_content(path, result.content, request))
        return hits

    def _hits_from_content(self, path: str, content: str, request: RetrievalRequest) -> list[RetrievalHit]:
        query_tokens = set(request.query.lower().split())
        lines = content.splitlines()
        hits: list[RetrievalHit] = []
        for index, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            lowered = line.lower()
            if query_tokens and not any(token in lowered for token in query_tokens):
                continue
            excerpt = line.strip()[: request.budget.max_hit_excerpt_chars]
            citation = self.citations.build(citation_type="file_line_range", source_id=self.source_id, source_type="file", ref=path, location=f"{path}:{index}", line_start=index, line_end=index, excerpt=excerpt)
            hits.append(RetrievalHit(source_id=self.source_id, source_type="file", title=Path(path).name, excerpt=excerpt, citation=citation, source_ref=citation.source_ref, metadata={"path": path, "line": index}))
            if len(hits) >= request.budget.max_hits_per_source:
                break
        return hits

    def status(self) -> dict[str, object]:
        return {"status": "ok", "source": self.source_id, "read_only": True}
