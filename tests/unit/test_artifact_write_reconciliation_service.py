from aipinho.services.artifacts.artifact_write_reconciliation_service import ArtifactWriteReconciliationService


def test_reconciliation_temp_cleanup(tmp_path):
    target = tmp_path / "reports" / "a.md"
    target.parent.mkdir()
    temp = target.with_name(target.name + ".aipinho_tmp")
    temp.write_text("tmp", encoding="utf-8")
    service = ArtifactWriteReconciliationService()
    assert service.temp_exists(str(target))
    assert service.cleanup_temp(str(target))
    assert not temp.exists()
