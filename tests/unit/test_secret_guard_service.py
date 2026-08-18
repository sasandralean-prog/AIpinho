from aipinho.services.security.secret_guard_service import SecretGuardService


def test_secret_guard_blocks_secret_filename():
    guard = SecretGuardService()
    assert guard.is_secret_path(".env") is True
    assert guard.is_secret_path("credentials.yaml") is True
    assert guard.is_secret_path("README.md") is False


def test_secret_guard_redacts_secret_content():
    redacted, warnings = SecretGuardService().redact("api_key = abc123\nBearer token-value")
    assert "abc123" not in redacted
    assert "token-value" not in redacted.lower()
    assert warnings
