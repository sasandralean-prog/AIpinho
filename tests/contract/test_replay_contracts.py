import pytest
from pydantic import ValidationError
from aipinho.schemas.replay.contracts import ReplayStatus, ReplaySnapshot, ReplaySnapshotMetadata

def test_replay_contract_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        ReplayStatus(extra=True)

def test_replay_snapshot_requires_sanitization_state():
    snapshot = ReplaySnapshot(metadata=ReplaySnapshotMetadata(capture_reason="unit"))
    assert snapshot.sanitization.sanitized is False
    assert ReplayStatus().side_effects_allowed is False
