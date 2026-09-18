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


def test_nonfatal_text_ineligible_file_is_omitted_without_security_violation(
    tmp_path,
):
    (tmp_path / "Main.kt").write_text(
        "fun main() = Unit",
        encoding="utf-8",
    )
    (tmp_path / "library.jar").write_bytes(b"binary")

    result = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=str(tmp_path),
            candidate_files=["Main.kt", "library.jar"],
            max_files=10,
        )
    )

    assert result.status == "partial"
    assert [item.path for item in result.selected_files] == ["Main.kt"]
    omitted = next(
        item
        for item in result.omitted_files
        if item.path == "library.jar"
    )
    assert omitted.blocked is True
    assert omitted.blocked_reason == "extension_not_allowed"
    assert result.violations == []
    assert "file_selection_nonfatal_policy_omissions" in result.warnings
    assert result.plan is not None
    assert (
        "FILE_SELECTION_NONFATAL_POLICY_OMISSIONS"
        in result.plan["selection_reason_codes"]
    )


def test_security_sensitive_omission_remains_a_violation_with_safe_context(
    tmp_path,
):
    (tmp_path / "Main.kt").write_text(
        "fun main() = Unit",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "TOKEN=secret",
        encoding="utf-8",
    )

    result = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=str(tmp_path),
            candidate_files=["Main.kt", ".env"],
            max_files=10,
        )
    )

    assert result.status == "partial"
    assert [item.path for item in result.selected_files] == ["Main.kt"]
    assert "secret_file" in result.violations
