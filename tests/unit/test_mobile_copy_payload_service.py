from aipinho.services.mobile_view_models.mobile_copy_payload_service import MobileCopyPayloadService
from aipinho.services.mobile_view_models.mobile_view_model_service import MobileViewModelService


def test_copy_payload_is_sanitized_and_contains_evidence():
    card = MobileViewModelService().dashboard().cards[0]
    payload = MobileCopyPayloadService().payload_for_card(card)

    assert payload.copy_policy == "sanitized_only"
    assert payload.summary
    assert payload.evidence
    assert payload.contains_secret is False

