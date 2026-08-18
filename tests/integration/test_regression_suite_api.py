from tests.replay_regression_helpers import client

def test_suite_api_loads_and_runs_core():
    suite=client.get("/api/v1/regression/suites/core_regression_suite")
    assert suite.status_code == 200
    run=client.post("/api/v1/regression/suites/core_regression_suite/run").json()["run"]
    assert run["side_effects_performed"] is False
    assert run["status"] == "passed"
