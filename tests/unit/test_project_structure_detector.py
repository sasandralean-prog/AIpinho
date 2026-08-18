from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.analysis.project_structure_detector import ProjectStructureDetector


def test_project_structure_detector_detects_config_src_tests_and_api():
    tree = ProjectTreeSummary(
        workspace="x",
        status="ok",
        top_level=["src", "tests", "config", "docs", "pyproject.toml"],
        candidate_files=["src/aipinho/app_factory.py", "src/aipinho/api/routers/governance_lifecycle_router.py", "src/aipinho/services/chat.py", "src/aipinho/schemas/chat.py"],
    )

    structures = ProjectStructureDetector().detect(tree)

    assert "python_project" in structures
    assert "fastapi_project" in structures
    assert "api_routes_present" in structures
    assert "config_first_layout" in structures
