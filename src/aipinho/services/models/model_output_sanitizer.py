from __future__ import annotations

import re


class ModelOutputSanitizer:
    SECRET_PATTERNS = (
        re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
        re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s]+"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    )

    def sanitize(self, text: str, *, max_chars: int | None = None) -> str:
        sanitized = text or ""
        for pattern in self.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        if max_chars is not None and len(sanitized) > max_chars:
            sanitized = sanitized[:max_chars] + "\n[TRUNCATED]"
        return sanitized

    def extract_llama_cli_completion(self, text: str, *, prompt: str) -> str:
        output = (text or "").replace("\r\n", "\n")
        if not output.strip():
            return ""
        if prompt and prompt in output:
            output = output.split(prompt, 1)[1]
        elif "\n> " in output:
            output = output.rsplit("\n> ", 1)[-1]
            if "\n\n" in output:
                output = output.split("\n\n", 1)[-1]
        output = self._strip_role_echo(output)
        if "\n[ Prompt:" in output:
            output = output.split("\n[ Prompt:", 1)[0]
        if "\nExiting..." in output:
            output = output.split("\nExiting...", 1)[0]
        fenced_json = self._fenced_json_suffix(output)
        if fenced_json:
            output = fenced_json
        return output.strip()

    def _strip_role_echo(self, text: str) -> str:
        output = text or ""
        for marker in ("\n```json", "\n{"):
            index = output.find(marker)
            if index > 0 and any(tag in output[:index] for tag in ("system:", "\nuser:", "\nassistant:")):
                return output[index + 1 :]
        return output

    def _fenced_json_suffix(self, text: str) -> str | None:
        output = text or ""
        fence_index = output.find("```json")
        if fence_index == -1:
            return None
        fenced = output[fence_index:]
        if fenced.startswith("```json"):
            return fenced
        return None

    def has_reasoning_content(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(marker in lowered for marker in ("[start thinking]", "[end thinking]", "<think>", "</think>"))

    def strip_reasoning_content(self, text: str) -> str:
        cleaned = text or ""
        for start, end in (("[Start thinking]", "[End thinking]"), ("<think>", "</think>")):
            while start.lower() in cleaned.lower():
                lowered = cleaned.lower()
                start_index = lowered.find(start.lower())
                end_index = lowered.find(end.lower(), start_index + len(start))
                if end_index == -1:
                    cleaned = cleaned[:start_index].strip()
                    break
                cleaned = (cleaned[:start_index] + cleaned[end_index + len(end):]).strip()
        return cleaned.strip()

    def has_llama_cli_error(self, text: str) -> bool:
        return any(line.lstrip().startswith("Error:") for line in (text or "").splitlines())

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_output_sanitizer", "secret_patterns": len(self.SECRET_PATTERNS)}
