from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PinhoForgeCommandCatalogQuery(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_command_{uuid4().hex}")
    query: str = ""
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    include_dangerous: bool = False
    include_blocked: bool = False
    max_results: int = 50


class PinhoForgeCommandPreviewRequest(AIpinhoModel):
    request_id: str = Field(default_factory=lambda: f"pinhoforge_command_{uuid4().hex}")
    command_id: str
    parameters: dict[str, str] = Field(default_factory=dict)


class PinhoForgeCommandCatalogResult(AIpinhoModel):
    request_id: str
    provider_id: str = "pinhoforge_studio"
    operation: Literal["search", "preview", "blocked"]
    status: Literal["completed", "preview_created", "blocked"]
    reason_code: str | None = None
    human_message: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    preview: dict[str, Any] | None = None
    execution_enabled: bool = False
    raw_hidden_by_default: bool = True
