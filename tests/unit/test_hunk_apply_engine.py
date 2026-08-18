from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.services.patching.apply.hunk_apply_engine import HunkApplyEngine


def test_hunk_apply_engine_requires_exact_context():
    engine = HunkApplyEngine()
    updated, result = engine.apply("# Old\n", PatchHunk(hunk_id="h", file_path="docs/a.md", original="# Old", replacement="# New"))
    assert result.applied is True
    assert updated == "# New\n"
    unchanged, failed = engine.apply("# Changed\n", PatchHunk(hunk_id="h", file_path="docs/a.md", original="# Old", replacement="# New"))
    assert failed.applied is False
    assert unchanged == "# Changed\n"
