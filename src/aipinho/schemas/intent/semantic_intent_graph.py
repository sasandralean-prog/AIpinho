from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

StateEffect = Literal[
    "none",
    "knowledge_only",
    "planning_only",
    "proposal_only",
    "workspace_mutation",
    "build_execution",
    "runtime_execution",
    "approval_command",
]
WorkspaceEffect = Literal["none", "immutable", "knowledge_only", "planning_only", "proposal_only", "mutable"]
FilesystemEffect = Literal["none", "prohibited", "knowledge_only", "proposal_only", "mutable"]
RuntimeEffect = Literal["none", "prohibited", "build_execution", "command_execution"]


class SemanticIntentGraph(AIpinhoModel):
    observational_intent: bool = False
    planning_intent: bool = False
    mutation_intent: bool = False
    execution_intent: bool = False
    approval_intent: bool = False
    knowledge_output: bool = False
    artifact_output: bool = False
    readonly_contract: bool = False
    state_effect: StateEffect = "none"
    workspace_effect: WorkspaceEffect = "none"
    filesystem_effect: FilesystemEffect = "none"
    runtime_effect: RuntimeEffect = "none"
    prohibited_effects: list[str] = Field(default_factory=list)
    requested_effects: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

