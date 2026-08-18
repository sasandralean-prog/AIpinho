from __future__ import annotations

from aipinho.services.security.secret_guard_service import SecretGuardService


class ContentSafetyService:
    def __init__(self, secret_guard: SecretGuardService | None = None) -> None:
        self.secret_guard = secret_guard or SecretGuardService()

    def is_binary_sample(self, data: bytes) -> bool:
        if b"\x00" in data:
            return True
        if not data:
            return False
        control = sum(1 for byte in data if byte < 9 or (13 < byte < 32))
        return (control / max(len(data), 1)) > 0.30

    def decode_text(self, data: bytes) -> tuple[str, list[str]]:
        warnings: list[str] = []
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
            warnings.append("decode_replacement_used")
        redacted, redaction_warnings = self.secret_guard.redact(text)
        return redacted, [*warnings, *redaction_warnings]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "content_safety"}
