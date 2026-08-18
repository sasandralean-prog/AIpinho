from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXFilterState(AIpinhoModel):
    severities: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    source_services: list[str] = Field(default_factory=list)
    include_internal: bool = False
    include_hidden: bool = False
