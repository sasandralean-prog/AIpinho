from tests.replay_regression_helpers import client, create_regression_candidate

def test_candidate_api_requires_approval_for_promotion():
    candidate=create_regression_candidate()
    blocked=client.post(f"/api/v1/regression/candidates/{candidate['candidate_id']}/promote",json={})
    assert blocked.status_code == 409
