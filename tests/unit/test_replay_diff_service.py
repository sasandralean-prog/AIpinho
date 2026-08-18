from aipinho.schemas.replay.contracts import ReplayRun
from aipinho.services.replay.replay_diff_service import ReplayDiffService

def test_diff_detects_changed_expectation():
    run = ReplayRun(case_id="case", snapshot_id="snapshot", result_payload={"write_allowed": False})
    diff = ReplayDiffService().create(run, {"write_allowed": True})
    assert diff.status == "diff"
