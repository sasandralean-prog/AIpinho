from aipinho.services.artifacts.artifact_backup_service import ArtifactBackupService


def test_backup_and_restore(tmp_path):
    target = tmp_path / "reports" / "a.md"
    target.parent.mkdir()
    target.write_text("old", encoding="utf-8")
    service = ArtifactBackupService(root=tmp_path / "backups")
    backup = service.create_backup(str(target), "artifact_write_run_abcdef")
    target.write_text("new", encoding="utf-8")
    assert service.restore_backup(backup.backup_id, str(target)) is True
    assert target.read_text(encoding="utf-8") == "old"


def test_backup_blocks_binary(tmp_path):
    target = tmp_path / "reports" / "a.md"
    target.parent.mkdir()
    target.write_bytes(b"\xff\xfe")
    service = ArtifactBackupService(root=tmp_path / "backups")
    try:
        service.create_backup(str(target), "artifact_write_run_abcdef")
    except ValueError as exc:
        assert str(exc) == "backup_binary_blocked"
