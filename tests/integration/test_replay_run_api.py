from tests.replay_regression_helpers import client, create_replay_case

def test_replay_run_and_diff_api():
    case=create_replay_case()
    run=client.post(f"/api/v1/replay/cases/{case['case_id']}/run").json()["run"]
    assert run["side_effects_performed"] is False
    diff=client.get(f"/api/v1/replay/runs/{run['run_id']}/diff")
    assert diff.status_code == 200
