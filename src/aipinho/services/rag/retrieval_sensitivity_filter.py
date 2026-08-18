from __future__ import annotations

import re

from aipinho.schemas.rag.retrieval_request import RetrievalHit


class RetrievalSensitivityFilter:
    SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password|passwd|secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{6,})")
    PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")

    def inspect_text(self, text: str) -> dict[str, object]:
        lowered = text.lower()
        reasons: list[str] = []
        if self.SECRET_PATTERN.search(text) or re.search(r"sk-[A-Za-z0-9]{12,}", text):
            reasons.append("secret_like_content")
        if self.PRIVATE_KEY_PATTERN.search(text):
            reasons.append("private_key")
        if "raw log" in lowered or "traceback (most recent call last)" in lowered:
            reasons.append("raw_log_content")
        if "\x00" in text:
            reasons.append("binary_content")
        return {"allowed": not reasons, "reasons": reasons, "text": self.redact(text)}

    def filter_hits(self, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        filtered: list[RetrievalHit] = []
        for hit in hits:
            check = self.inspect_text(hit.excerpt)
            if check["allowed"]:
                hit.excerpt = str(check["text"])
                filtered.append(hit)
            else:
                hit.blocked = True
                hit.blocked_reason = ",".join(check["reasons"])
        return filtered

    def redact(self, text: str) -> str:
        text = self.SECRET_PATTERN.sub(r"\1=[REDACTED]", text)
        text = re.sub(r"sk-[A-Za-z0-9]{12,}", "sk-[REDACTED]", text)
        return text

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_sensitivity_filter", "secret_retrieval_enabled": False, "raw_log_retrieval_enabled": False}
