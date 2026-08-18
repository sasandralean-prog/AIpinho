from aipinho.services.security.local_token_service import LocalTokenService


def test_token_auth_valid_missing_invalid_and_redaction(tmp_path):
    svc = LocalTokenService(tmp_path / "token.json")
    token = svc.create_token().token
    assert svc.validate_authorization(f"Bearer {token}") is True
    assert svc.validate_authorization(None) is False
    assert svc.validate_authorization("Bearer wrong") is False
    assert svc.redact(f"Bearer {token}") == "Bearer [REDACTED_TOKEN]"
    assert svc.status()["plaintext_available"] is False
