from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.output_contract import OutputContract
from aipinho.schemas.prompts.prompt_budget import PromptBudget
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.prompts.safety_envelope import SafetyEnvelope

PromptPurpose = Literal["chat", "project_report", "code_analysis", "self_analysis", "capability_explanation", "task_preview"]


class PromptAssemblyRequest(AIpinhoModel):
    purpose: PromptPurpose
    role_id: str
    user_message: str = ""
    intent_map: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    session_context: dict[str, Any] = Field(default_factory=dict)
    file_context_bundle: dict[str, Any] = Field(default_factory=dict)
    project_report: dict[str, Any] = Field(default_factory=dict)
    retrieval_context_bundle: dict[str, Any] = Field(default_factory=dict)
    context_injection_plan_id: str | None = None
    context_injection_plan: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    context_items: list[PromptContextItem] = Field(default_factory=list)
    output_contract_type: str = "plain_text"
    model_id: str = "stub.default"
    include_trace: bool = False


class PromptAssembly(AIpinhoModel):
    assembly_id: str = Field(default_factory=lambda: f"prompt_assembly_{uuid4().hex}")
    purpose: PromptPurpose
    model_id: str = "stub.default"
    role_id: str
    messages: list[PromptMessage]
    context_items: list[PromptContextItem] = Field(default_factory=list)
    budget: PromptBudget = Field(default_factory=PromptBudget)
    output_contract: OutputContract
    safety_envelope: SafetyEnvelope
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)


class PromptPreview(AIpinhoModel):
    assembly: PromptAssembly
    model_request: ModelRequest
    invokes_model: bool = False
    side_effects: bool = False
