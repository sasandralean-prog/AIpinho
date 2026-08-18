from aipinho.services.chat.chat_model_fallback_service import ChatModelFallbackService


def test_chat_model_fallback_hides_rejected_content():
    fallback = ChatModelFallbackService().build("rejected")
    assert fallback.fallback_used is True
    assert fallback.rejected_model_content_hidden is True
    assert fallback.safe_message
