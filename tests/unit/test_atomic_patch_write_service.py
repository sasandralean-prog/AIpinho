from aipinho.services.patching.apply.atomic_patch_write_service import AtomicPatchWriteService


def test_atomic_patch_write_blocks_existing_temp(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("old", encoding="utf-8")
    target.with_name("a.txt.aipinho_patch_tmp").write_text("tmp", encoding="utf-8")
    try:
        AtomicPatchWriteService().write(target, "new")
    except ValueError as exc:
        assert str(exc) == "patch_temp_file_exists"
    assert target.read_text(encoding="utf-8") == "old"
