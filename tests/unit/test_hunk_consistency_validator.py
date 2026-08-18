from aipinho.services.patching.quality.hunk_consistency_validator import HunkConsistencyValidator
from aipinho.services.patching.quality.unified_diff_parser import UnifiedDiffParser


def test_hunk_consistency_validator_blocks_stale_removed_line():
    diff = "--- a/docs/note.md\n+++ b/docs/note.md\n@@ -1 +1 @@\n-# Old\n+# New\n"
    parse = UnifiedDiffParser().parse(diff)
    result = HunkConsistencyValidator().validate(parse, {"docs/note.md": "# Already changed\n"})
    assert result.valid is False
    assert any(finding.category == "hunk_validation" for finding in result.findings)
