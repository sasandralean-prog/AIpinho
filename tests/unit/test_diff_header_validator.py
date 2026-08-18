from aipinho.services.patching.quality.diff_header_validator import DiffHeaderValidator
from aipinho.services.patching.quality.unified_diff_parser import UnifiedDiffParser


def test_diff_header_validator_blocks_absolute_target():
    diff = "--- a/docs/note.md\n+++ /etc/passwd\n@@ -1 +1 @@\n-a\n+b\n"
    parse = UnifiedDiffParser().parse(diff)
    findings = DiffHeaderValidator().validate(parse)
    assert any(finding.category == "unsafe_path" and finding.blocking for finding in findings)
