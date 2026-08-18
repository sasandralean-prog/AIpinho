from __future__ import annotations


class DebugSanitizer:
    SECRET_KEYS = {"token", "api_key", "secret", "password"}

    def sanitize(self, value: object) -> object:
        if isinstance(value, dict):
            cleaned: dict[str, object] = {}
            for key, item in value.items():
                key_text = str(key)
                if any(secret_key in key_text.lower() for secret_key in self.SECRET_KEYS):
                    cleaned[key_text] = "[REDACTED]"
                else:
                    cleaned[key_text] = self.sanitize(item)
            return cleaned
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            return self._sanitize_text(value)
        return value

    def _sanitize_text(self, text: str) -> str:
        lowered = text.lower()
        if "sk-" in lowered or "api_key=" in lowered or "password=" in lowered:
            return "[REDACTED_TEXT]"
        return text
