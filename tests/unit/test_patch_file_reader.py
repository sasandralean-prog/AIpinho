from patch_fixtures import patch_workspace
from aipinho.services.patching.patch_file_reader import PatchFileReader
from aipinho.services.patching.patch_target_guard import PatchTargetGuard


def test_patch_file_reader_reads_text_and_blocks_binary(tmp_path):
    workspace = patch_workspace(tmp_path)
    guard = PatchTargetGuard()
    affected = guard.validate(str(workspace), "src/app.py")
    checked, content = PatchFileReader().read(affected)
    assert checked.original_hash
    assert "old" in content
    (workspace / "src" / "bad.py").write_bytes(b"\xff\xfe")
    checked, _ = PatchFileReader().read(guard.validate(str(workspace), "src/bad.py"))
    assert checked.status == "blocked"
    assert "binary_file" in checked.blocked_reasons
