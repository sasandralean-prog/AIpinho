from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.intent.intent_map import IntentMap
from aipinho.schemas.policy.policy_trace import PolicyTraceItem


class PromptAnalysisResponse(AIpinhoModel):
    intent_map: IntentMap
    warnings: list[str] = Field(default_factory=list)
    trace: list[PolicyTraceItem] = Field(default_factory=list)


class PromptContractPreviewResponse(AIpinhoModel):
    intent_map: IntentMap
    policy_preview: dict[str, object]
    warnings: list[str] = Field(default_factory=list)