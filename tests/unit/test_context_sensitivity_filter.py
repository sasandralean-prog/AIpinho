from aipinho.services.context.context_core import ContextSensitivityFilter

def test_sensitivity_token_password_private_key():
    ok,red,reasons=ContextSensitivityFilter().scan('Bearer abcdef123 password=123 -----BEGIN PRIVATE KEY-----')
    assert not ok; assert '[REDACTED_SECRET]' in red; assert reasons
