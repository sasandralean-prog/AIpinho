from tests.replay_regression_helpers import client, create_regression_candidate

def test_regression_report_available_for_case_run():
    candidate=create_regression_candidate()
    promoted=client.post(f"/api/v1/regression/candidates/{candidate['candidate_id']}/promote",json={"approved":True,"validation_passed":True}).json()
    run=client.post(f"/api/v1/regression/cases/{promoted['case']['case_id']}/run").json()["run"]
    report=client.get(f"/api/v1/regression/runs/{run['run_id']}/report")
    assert report.status_code == 200
