from __future__ import annotations


class AntiTruncationService:
    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max(200, int(max_chars))

    def apply(self, message: str) -> tuple[str, list[str]]:
        if len(message) <= self.max_chars:
            return message, []
        suffix = "\n\n[Resposta encurtada pelo limite configurado. Use o modo preview/debug para mais detalhes estruturados.]"
        available = max(0, self.max_chars - len(suffix))
        return message[:available].rstrip() + suffix, ["response_truncated"]