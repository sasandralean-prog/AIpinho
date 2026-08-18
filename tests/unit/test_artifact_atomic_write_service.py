from aipinho.services.artifacts.artifact_atomic_write_service import ArtifactAtomicWriteService


def test_atomic_write_temp_cleanup_and_hash(tmp_path):
    target = tmp_path / "reports" / "a.md"
    result = ArtifactAtomicWriteService().write_text_atomic(str(target), "# A\n", overwrite=False)
    assert result.status == "completed"
    assert target.read_text(encoding="utf-8") == "# A\n"
    assert not target.with_name(target.name + ".aipinho_tmp").exists()
    blocked = ArtifactAtomicWriteService().write_text_atomic(str(target), "# B\n", overwrite=False)
    assert blocked.status == "blocked"


def test_atomic_write_blocks_existing_temp(tmp_path):
    target = tmp_path / "reports" / "a.md"
    target.parent.mkdir()
    target.with_name(target.name + ".aipinho_tmp").write_text("tmp", encoding="utf-8")
    result = ArtifactAtomicWriteService().write_text_atomic(str(target), "# A\n", overwrite=False)
    assert result.status == "blocked"
    assert "temp_exists" in result.blocked_reasons
