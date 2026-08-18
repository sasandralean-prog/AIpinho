from __future__ import annotations

from aipinho.services.debugger.debug_sanitizer import DebugSanitizer


class DebuggerSanitizer(DebugSanitizer):
    MAX_TEXT = 4000

    def sanitize(self, value: object) -> object:
        cleaned = super().sanitize(value)
        return self._truncate(cleaned)

    def _truncate(self, value: object) -> object:
        if isinstance(value, dict):
            hidden = {"raw_prompt", "raw_output", "raw_log", "full_file_content", "file_content"}
            return {str(key): "[HIDDEN_BY_DEBUGGER_POLICY]" if str(key).lower() in hidden else self._truncate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._truncate(item) for item in value]
        if isinstance(value, str) and len(value) > self.MAX_TEXT:
            return value[: self.MAX_TEXT] + "...[TRUNCATED]"
        return value

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "debugger_sanitizer", "raw_hidden_by_default": True, "secrets_redacted": True}
