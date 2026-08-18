from __future__ import annotations

import unicodedata
import re


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\bn[?�]o\b", "nao", value, flags=re.IGNORECASE)
    return " ".join(value.casefold().split())


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(term) in normalized for term in terms)
