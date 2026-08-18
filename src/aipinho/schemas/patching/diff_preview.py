from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class DiffPreview(AIpinhoModel):
    diff_text: str = ""
    truncated: bool = False
    chars: int = 0
    added_lines: int = 0
    removed_lines: int = 0
