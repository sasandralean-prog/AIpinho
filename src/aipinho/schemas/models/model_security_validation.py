from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelSecurityValidation(AIpinhoModel):
    model_id: str
    status: str
    path: str | None = None
    allowed_root: bool = False
    extension_valid: bool = False
    network_path: bool = False
    traversal_detected: bool = False
    symlink_detected: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
