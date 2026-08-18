from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.analysis.architecture_analyzer import ArchitectureAnalyzer


def test_architecture_analyzer_reports_evidence_and_limitations():
    tree = ProjectTreeSummary(workspace="x", status="ok", top_level=["config", "src"], candidate_files=["src/a.py", "config/policy.yaml"])
    context = FileContextBundle(bundle_id="b", workspace="x", status="partial", items=[FileContextItem(path="src/a.py", status="included", content="x")])

    findings = ArchitectureAnalyzer().analyze(tree, context, ["config_first_layout", "services_present", "schemas_present"])

    assert any(item.category == "scope" for item in findings)
    assert any(item.category == "limitations" for item in findings)
