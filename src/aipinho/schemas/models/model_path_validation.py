from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

PathValidationKind = Literal["model", "executable"]
PathValidationStatus = Literal["valid", "blocked", "degraded", "unavailable", "disabled"]


class ModelPathValidation(AIpinhoModel):
    kind: PathValidationKind
    path: str | None = None
    configured: bool = False
    valid: bool = False
    exists: bool = False
    is_file: bool = False
    extension_valid: bool = False
    allowed_root: bool = False
    forbidden_root: bool = False
    network_path: bool = False
    size_bytes: int | None = None
    status: PathValidationStatus = "unavailable"
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
