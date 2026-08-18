from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PathPolicy(AIpinhoModel):
    normalize_case_on_windows: bool = True
    resolve_before_check: bool = True
    block_relative_escape: bool = True
    block_unc_paths: bool = True
    block_device_paths: bool = True
    block_reserved_names: bool = True
    block_symlink_escape: bool = True
    protected_patterns: list[str] = Field(default_factory=list)
    allowed_extensions_for_text_read: list[str] = Field(default_factory=list)
    blocked_extensions: list[str] = Field(default_factory=list)
