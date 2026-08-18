from aipinho.schemas.analysis.file_selection import FileSelectionCandidate, FileSelectionResult
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.services.analysis.file_context_builder import FileContextBuilder


def test_file_context_builder_reads_via_readonly_executor_and_blocks_binary(tmp_path):
    (tmp_path / "README.md").write_text("AIpinho", encoding="utf-8")
    (tmp_path / "archive.zip").write_bytes(b"PKbinary")
    selection = FileSelectionResult(
        status="ok",
        selected_files=[
            FileSelectionCandidate(path="README.md", score=100, size_bytes=7),
            FileSelectionCandidate(path="archive.zip", score=100, size_bytes=10),
        ],
    )

    bundle = FileContextBuilder().build_context(ProjectAnalysisRequest(workspace=str(tmp_path), include_trace=True), selection)

    assert bundle.status == "partial"
    included = [item for item in bundle.items if item.status == "included"]
    blocked = [item for item in bundle.items if item.status == "blocked"]
    assert included[0].content == "AIpinho"
    assert blocked and "blocked_extension" in blocked[0].violations
