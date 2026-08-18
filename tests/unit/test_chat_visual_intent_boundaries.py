from aipinho.services.chat.chat_service import ChatService


def test_sprint_word_does_not_trigger_visual_analysis() -> None:
    service = ChatService()

    assert service._requests_visual_or_ocr_analysis(
        "Analise o projeto e organize o trabalho em sprints pequenos.",
    ) is False


def test_explicit_screenshot_request_triggers_visual_analysis() -> None:
    service = ChatService()

    assert service._requests_visual_or_ocr_analysis(
        "Analise este screenshot e descreva o erro visivel.",
    ) is True


def test_aguarde_does_not_trigger_memory_candidate() -> None:
    service = ChatService()

    assert service._requests_memory_candidate(
        "Gere o preview e aguarde approval antes de escrever.",
    ) is False


def test_explicit_memory_request_triggers_memory_candidate() -> None:
    service = ChatService()

    assert service._requests_memory_candidate(
        "Guarde esta regra como memoria candidata.",
    ) is True
