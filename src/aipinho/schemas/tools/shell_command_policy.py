from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ShellCommandCategory = Literal[
    "readonly_shell",
    "test_shell",
    "build_shell",
    "package_shell",
    "write_shell",
    "destructive_shell",
    "git_read_shell",
    "git_write_shell",
    "network_shell",
    "process_control_shell",
    "unknown_shell",
]


class ShellCommandClassification(AIpinhoModel):
    command_id: str
    normalized_command: str
    working_dir: str | None = None
    category: ShellCommandCategory = "unknown_shell"
    policy_decision: str = "blocked"
    risk_score: str = "high"
    expected_side_effects: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    trace: list[dict[str, object]] = Field(default_factory=list)
