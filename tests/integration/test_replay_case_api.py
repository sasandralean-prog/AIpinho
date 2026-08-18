from tests.replay_regression_helpers import create_replay_case

def test_replay_case_api():
    case=create_replay_case()
    assert case["snapshot_id"].startswith("replay_snapshot_")
