from tests.replay_regression_helpers import client, create_regression_candidate, create_replay_case

def test_replay_regression_harness_flow():
    assert client.get("/api/v1/replay/status").json()["side_effects_allowed"] is False
    case=create_replay_case()
    replay_run=client.post(f"/api/v1/replay/cases/{case['case_id']}/run").json()["run"]
    assert replay_run["model_real_inference"] is False
    assert replay_run["patch_apply_executed"] is False
    candidate=create_regression_candidate()
    blocked=client.post(f"/api/v1/regression/candidates/{candidate['candidate_id']}/promote",json={})
    assert blocked.status_code == 409
    promoted=client.post(f"/api/v1/regression/candidates/{candidate['candidate_id']}/promote",json={"approved":True,"validation_passed":True}).json()
    result=client.post(f"/api/v1/regression/cases/{promoted['case']['case_id']}/run").json()["run"]
    assert result["status"]=="passed"
    report=client.get(f"/api/v1/regression/runs/{result['run_id']}/report")
    assert report.status_code == 200
