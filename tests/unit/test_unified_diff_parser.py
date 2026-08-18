from aipinho.services.patching.quality.unified_diff_parser import UnifiedDiffParser


def test_unified_diff_parser_extracts_file_and_hunks():
    diff = "--- a/docs/note.md\n+++ b/docs/note.md\n@@ -1 +1 @@\n-# Old\n+# New\n"
    result = UnifiedDiffParser().parse(diff)
    assert result.valid is True
    assert result.affected_files == ["docs/note.md"]
    assert result.added_lines == 1
    assert result.removed_lines == 1
    assert result.hunks[0].removed_lines == ["# Old"]


def test_unified_diff_parser_rejects_binary_diff():
    result = UnifiedDiffParser().parse("GIT binary patch\n")
    assert result.valid is False
    assert any(finding.category == "binary_diff" for finding in result.findings)
