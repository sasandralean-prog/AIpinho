from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner


def test_artifact_secret_scanner_detects_and_redacts():
    scanner = ArtifactSecretScanner()
    assert scanner.has_secret("api_key=abc123")
    assert scanner.has_secret("token: xyz")
    assert scanner.has_secret("-----BEGIN TEST PRIVATE KEY-----")
    assert "[REDACTED]" in scanner.redact("password=secret")
