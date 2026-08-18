from aipinho.schemas.replay.contracts import ReplaySnapshot, ReplaySnapshotMetadata, ReplayInputBundle
from aipinho.services.replay.replay_snapshot_sanitizer import ReplaySnapshotSanitizer

def test_sanitizer_redacts_private_key_like_payload():
    snapshot = ReplaySnapshot(metadata=ReplaySnapshotMetadata(capture_reason="unit"), input_bundle=ReplayInputBundle(prompt="-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----"))
    sanitized = ReplaySnapshotSanitizer().sanitize(snapshot)
    assert sanitized.sanitization.sanitized is True
    assert "PRIVATE KEY" not in sanitized.input_bundle.prompt
