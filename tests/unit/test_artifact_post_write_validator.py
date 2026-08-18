from hashlib import sha256

from aipinho.services.artifacts.artifact_post_write_validator import ArtifactPostWriteValidator


def test_post_write_validator_passes_and_fails(tmp_path):
    workspace = tmp_path / "workspace"
    target = workspace / "reports" / "a.md"
    target.parent.mkdir(parents=True)
    content = "# A\n"
    target.write_text(content, encoding="utf-8", newline="\n")
    raw = target.read_bytes()
    result = ArtifactPostWriteValidator().validate(workspace=str(workspace), target_path=str(target), expected_hash=sha256(raw).hexdigest(), expected_bytes=len(raw), temp_path=str(target) + ".aipinho_tmp")
    assert result.passed is True
    failed = ArtifactPostWriteValidator().validate(workspace=str(workspace), target_path=str(target), expected_hash="bad", expected_bytes=999, temp_path=str(target) + ".aipinho_tmp")
    assert failed.passed is False
    assert "post_write_hash_mismatch" in failed.blocked_reasons
