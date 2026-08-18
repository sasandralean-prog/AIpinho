from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWritePolicyStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    mode: str = "approved_non_code_writes"
    direct_payload_write_enabled: bool = False
    source_code_write_enabled: bool = False
    active_config_write_enabled: bool = False
    script_write_enabled: bool = False
    approved_preview_required: bool = True
    approval_required: bool = True
    hash_lock_required: bool = True
    target_lock_required: bool = True
    post_write_validation_required: bool = True
    allowed_extensions: list[str] = Field(default_factory=list)
    allowed_base_dirs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
