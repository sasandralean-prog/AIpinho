from aipinho.services.debugger.debug_sanitizer import DebugSanitizer


def test_debug_sanitizer_redacts_secret_keys():
    data = DebugSanitizer().sanitize({"token": "abc", "nested": {"password": "123"}, "ok": "value"})
    assert data["token"] == "[REDACTED]"
    assert data["nested"]["password"] == "[REDACTED]"
    assert data["ok"] == "value"
