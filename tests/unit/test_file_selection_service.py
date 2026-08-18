from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.services.analysis.file_selection_service import FileSelectionService


def test_file_selection_prioritizes_focus_and_blocks_secret(tmp_path):
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('main')", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")

    result = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=str(tmp_path),
            candidate_files=["README.md", "src/main.py", ".env"],
            focus_paths=["src/main.py"],
            max_files=2,
        )
    )

    assert result.status in {"partial", "ok"}
    assert result.selected_files[0].path == "src/main.py"
    assert any(item.path == ".env" and item.blocked for item in result.omitted_files)
    assert "secret_file" in result.violations
