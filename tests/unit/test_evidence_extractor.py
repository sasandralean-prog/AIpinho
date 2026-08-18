from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.reports.evidence_extractor import EvidenceExtractor


def test_evidence_extractor_builds_file_tree_absence_and_line_ranges():
    extractor = EvidenceExtractor()
    bundle = FileContextBundle(
        bundle_id="b",
        workspace="w",
        status="partial",
        items=[
            FileContextItem(path="src/app.py", status="included", content="one\nFastAPI app\nthree\nfour\nfive", metadata={"audit_event_id": "audit_1"}),
            FileContextItem(path=".env", status="blocked", violations=["secret_file"]),
        ],
    )
    tree = ProjectTreeSummary(workspace="w", status="ok", top_level=["src"], candidate_files=["src/app.py"], blocked_paths=[".env"])

    file_evidence = extractor.extract_from_file_context(bundle)
    tree_evidence = extractor.extract_from_tree(tree)
    absence = extractor.extract_absence_evidence("tests/**/*.py", tree)
    ranges = extractor.find_line_ranges("a\nneedle here\nc", ["needle"])

    assert file_evidence[0].path == "src/app.py"
    assert file_evidence[0].line_start == 1
    assert file_evidence[0].line_end
    assert len(file_evidence[0].excerpt or "") <= 600
    assert not any(item.path == ".env" and item.source_type == "file" for item in file_evidence)
    assert any(item.path == ".env" and item.source_type == "metadata" for item in tree_evidence)
    assert absence.source_type == "absence"
    assert ranges == [(2, 3)]
