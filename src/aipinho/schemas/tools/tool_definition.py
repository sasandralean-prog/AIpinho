from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from aipinho.schemas.common.base import AIpinhoModel

ToolCategory = Literal["filesystem", "shell", "git", "patch", "android", "web", "model", "memory", "rag", "unknown"]
ToolRiskLevel = Literal["low", "medium", "high", "critical"]


class ToolDefinition(AIpinhoModel):
    tool_id: str
    name: str
    category: ToolCategory = "unknown"
    adapter: str
    action: str
    capability: str
    side_effect: bool = False
    requires_approval: bool = False
    enabled: bool = True
    dry_run_supported: bool = True
    execute_supported: bool = False
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel = "low"
    description: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_safety_flags(self) -> "ToolDefinition":
        if self.side_effect and not self.requires_approval:
            raise ValueError("side_effect_tool_requires_approval")
        if not self.dry_run_supported:
            raise ValueError("initial_tools_must_support_dry_run")
        return self
