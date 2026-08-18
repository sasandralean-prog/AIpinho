from aipinho.services.artifacts.artifact_content_validator import ArtifactContentValidator


def test_artifact_content_validator_blocks_secret_binary_executable_patch():
    validator = ArtifactContentValidator()
    assert validator.validate("hello", fmt="markdown").valid is True
    assert "secret_content" in validator.validate("api_key=abc123", fmt="markdown").blocked_reasons
    assert "binary_content" in validator.validate(b"\xff\x00", fmt="markdown").blocked_reasons
    assert "executable_content" in validator.validate("#!/bin/sh\necho x", fmt="markdown").blocked_reasons
    assert "patch_payload" in validator.validate("diff --git a b", fmt="text", artifact_type="export").blocked_reasons
