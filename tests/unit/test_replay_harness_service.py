from aipinho.services.replay.replay_harness_service import ReplayHarnessService

def test_replay_status_is_safe():
    status = ReplayHarnessService().status()
    assert status.enabled is True
    assert status.side_effects_allowed is False
    assert status.model_real_inference_allowed is False
