
from aipinho.services.legacy_rag.legacy_core import LegacySanitizationService


def test_legacy_rag_sanitizer_removes_secret_and_legacy_root():
    service = LegacySanitizationService()
    text, redactions = service.sanitize_text("token=QswisSWC5zAY6OHHKnA4vk8gfWBiaQyi6fSQvRoG75k\nC:\\Dev\\AI\\coding-brain-supervisor")
    assert "[REDACTED_SECRET]" in text
    assert "[LEGACY_SOURCE_ROOT]" in text
    assert redactions
