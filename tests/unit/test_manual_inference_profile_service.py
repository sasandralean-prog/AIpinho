from manual_inference_test_helpers import PROFILE_ID, profile_config
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService


def test_manual_inference_profile_service_lists_manual_only_profile():
    service = ManualInferenceProfileService(config=profile_config(enabled=False))
    profiles = service.list_profiles()
    assert profiles[0]["profile_id"] == PROFILE_ID
    assert profiles[0]["enabled"] is False
    assert profiles[0]["manual_only"] is True
    assert profiles[0]["allow_chat_auto_use"] is False


def test_manual_inference_profile_service_warns_when_profile_allows_chat_auto_use():
    service = ManualInferenceProfileService(config=profile_config(enabled=True, allow_chat_auto_use=True))
    profile = service.load_profiles()[0]
    assert "chat_auto_use_forbidden" in profile.warnings
    assert service.status()["status"] == "degraded"
