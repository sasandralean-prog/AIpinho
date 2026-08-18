from aipinho.services.mobile_view_models.mobile_view_model_service import MobileViewModelService


def _assert_card_dogmas(card) -> None:
    answers = card.answers
    assert answers.what_is_happening
    assert answers.why_is_it_happening
    assert answers.is_it_safe.answer in {"safe", "caution", "risky", "blocked", "unknown"}
    assert answers.is_it_safe.reason
    assert answers.what_can_i_do_now
    assert answers.what_evidence_supports_this is not None
    assert answers.can_copy_sanitized_summary is True


def test_all_mobile_view_models_return_humanized_cards_with_dogmas():
    service = MobileViewModelService()
    screens = [
        service.dashboard(),
        service.chat("chat_test"),
        service.pipeline("task_test"),
        service.debugger(),
        service.config(),
    ]

    for screen in screens:
        assert screen.state.raw_default_visible is False
        assert screen.state.ui_decides_policy is False
        assert screen.state.ui_decides_safety is False
        assert screen.state.ui_decides_final_status is False
        assert screen.cards
        for card in screen.cards:
            _assert_card_dogmas(card)
            assert card.copy_payload["summary_available"] is True


def test_mobile_status_exposes_phase_flags():
    status = MobileViewModelService().status()

    assert status["mobile_view_models_enabled"] is True
    assert status["mobile_phase_1_observability"] is True
    assert status["mobile_phase_5_multimodal"] is True
    assert status["ui_decides_policy"] is False
    assert status["raw_default_visible"] is False
