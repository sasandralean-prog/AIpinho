from aipinho.services.mobile_view_models.mobile_sanitizer_service import MobileSanitizerService


def test_sanitizer_redacts_secrets_and_user_paths():
    service = MobileSanitizerService()
    text = r"token: abc123 C:\Users\rafae\Documents\project"

    sanitized = service.sanitize_text(text)

    assert "abc123" not in sanitized
    assert r"C:\Users\rafae" not in sanitized
    assert "[REDACTED]" in sanitized

