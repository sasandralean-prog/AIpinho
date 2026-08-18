from aipinho.services.patching.unified_diff_builder import UnifiedDiffBuilder


def test_unified_diff_builder_outputs_preview_only_diff():
    diff = UnifiedDiffBuilder().build("docs/note.md", "# Old\n", "# New\n")
    assert "--- a/docs/note.md" in diff.diff_text
    assert "+++ b/docs/note.md" in diff.diff_text
    assert diff.added_lines == 1
    assert diff.removed_lines == 1
