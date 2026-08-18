from tests.replay_regression_helpers import client, create_regression_candidate

def test_candidate_promotes_to_case_with_approval_and_validation():
    candidate=create_regression_candidate()
    promoted=client.post(f"/api/v1/regression/candidates/{candidate['candidate_id']}/promote",json={"approved":True,"validation_passed":True})
    assert promoted.status_code == 200
    case_id=promoted.json()["case"]["case_id"]
    assert client.get(f"/api/v1/regression/cases/{case_id}").status_code == 200
