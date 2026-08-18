from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.services.analysis.project_tree_service import ProjectTreeService


def test_project_tree_summary_lists_candidates_without_content(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    (tmp_path / "asset.png").write_bytes(b"png")

    tree = ProjectTreeService().build_tree_summary(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert tree.status == "ok"
    assert "README.md" in tree.candidate_files
    assert "src/app.py" in tree.candidate_files
    assert ".env" not in tree.candidate_files
    assert any(path in tree.blocked_paths for path in [".env", "asset.png"])
