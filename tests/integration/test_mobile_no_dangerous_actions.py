from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


def test_mobile_view_models_do_not_expose_dangerous_actions():
    client = TestClient(create_app())
    paths = [
        "/api/v1/mobile/view-model/dashboard",
        "/api/v1/mobile/view-model/chat/chat_test",
        "/api/v1/mobile/view-model/pipeline/task_test",
        "/api/v1/mobile/view-model/debugger",
        "/api/v1/mobile/view-model/config",
    ]
    dangerous = {"apply_patch", "run_shell", "run_git", "run_model_real_inference", "mutate_memory"}

    for path in paths:
        data = client.get(path).json()
        for card in data["cards"]:
            for action in card["safe_actions"]:
                assert action["kind"] not in dangerous
                assert not str(action["endpoint_ref"]).startswith("/v2")

