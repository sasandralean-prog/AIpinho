from aipinho.schemas.replay.contracts import ReplayCaptureRequest
from aipinho.services.replay.replay_snapshot_builder import ReplaySnapshotBuilder

def test_builder_freezes_input_and_decision_bundle():
    snapshot = ReplaySnapshotBuilder().build(ReplayCaptureRequest(reason="unit", task_id="task", snapshot_payload={"decision_bundle":{"policy_decision":{"write_allowed":False}}}))
    assert snapshot.input_bundle.task_id == "task"
    assert snapshot.decision_bundle.policy_decision["write_allowed"] is False
