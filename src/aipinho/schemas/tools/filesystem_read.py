from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

PathKind = Literal["file", "directory", "missing", "other"]


class FilesystemEntry(AIpinhoModel):
    name: str
    kind: PathKind
    size: int | None = None
    extension: str | None = None
    blocked: bool = False
    blocked_reasons: list[str] = Field(default_factory=list)


class FilesystemReadMetadata(AIpinhoModel):
    path_kind: PathKind
    exists: bool
    size: int | None = None
    extension: str | None = None
    is_binary: bool = False
    bytes_read: int = 0
    entries_returned: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
