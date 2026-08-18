from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ReportSection(AIpinhoModel):
    section_id: str
    title: str
    content: str = ""
    items: list[dict[str, Any]] = Field(default_factory=list)
