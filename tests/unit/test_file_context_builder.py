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


def test_evidence_repair_can_expand_internal_preview_when_full_file_fits_budget(
    tmp_path,
):
    content = "fun value() = 1\n" * 1_600
    target = tmp_path / "Large.kt"
    target.write_bytes(content.encode("utf-8"))
    size = target.stat().st_size
    selection = FileSelectionResult(
        status="ok",
        selected_files=[
            FileSelectionCandidate(
                path="Large.kt",
                score=100,
                size_bytes=size,
            )
        ],
    )
    builder = FileContextBuilder()

    normal = builder.build_context(
        ProjectAnalysisRequest(
            workspace=str(tmp_path),
            focus_paths=["Large.kt"],
            max_files=1,
            max_total_bytes=120_000,
            max_file_bytes=120_000,
        ),
        selection,
    )
    repair = builder.build_context(
        ProjectAnalysisRequest(
            workspace=str(tmp_path),
            goal="evidence_repair_analysis",
            focus_paths=["Large.kt"],
            max_files=1,
            max_total_bytes=120_000,
            max_file_bytes=120_000,
        ),
        selection,
    )

    assert normal.status == "partial"
    assert normal.items[0].content_truncated is True
    assert len(normal.items[0].content or "") < len(content)
    assert repair.status == "ok"
    assert repair.items[0].content == content
    assert repair.items[0].content_truncated is False
    assert repair.items[0].metadata[
        "content_preview_override_used"
    ] is True
    assert repair.total_bytes_read == size


def test_evidence_repair_does_not_expand_preview_when_file_exceeds_budget(
    tmp_path,
):
    content = "x" * 140_000
    target = tmp_path / "TooLarge.kt"
    target.write_text(content, encoding="utf-8")
    size = target.stat().st_size
    selection = FileSelectionResult(
        status="ok",
        selected_files=[
            FileSelectionCandidate(
                path="TooLarge.kt",
                score=100,
                size_bytes=size,
            )
        ],
    )

    bundle = FileContextBuilder().build_context(
        ProjectAnalysisRequest(
            workspace=str(tmp_path),
            goal="evidence_repair_analysis",
            focus_paths=["TooLarge.kt"],
            max_files=1,
            max_total_bytes=120_000,
            max_file_bytes=120_000,
        ),
        selection,
    )

    assert bundle.status == "partial"
    assert bundle.items[0].content_truncated is True
    assert bundle.items[0].metadata[
        "content_preview_override_used"
    ] is False
    assert bundle.total_bytes_read == 120_000
