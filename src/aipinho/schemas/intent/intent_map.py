from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.intent.ambiguity import AmbiguityResult
from aipinho.schemas.intent.intent_evidence import IntentEvidence
from aipinho.schemas.intent.prompt_segment import PromptSegment
from aipinho.schemas.intent.risk import RiskLevel, RiskResult
from aipinho.schemas.intent.semantic_intent_graph import SemanticIntentGraph
from aipinho.schemas.intent.workspace_resolution import TargetReference, WorkspaceResolution
from aipinho.schemas.intent.workspace_reference import WorkspaceReference
from aipinho.schemas.policy.policy_trace import PolicyTraceItem

IntentType = Literal[
    "conversation",
    "self_analysis",
    "capability_explanation",
    "in_chat_final_report",
    "readonly_analysis",
    "artifact_generation",
    "filesystem_write_request",
    "file_modification_request",
    "project_generation_request",
    "android_project_generation",
    "artifact_build_request",
    "patch_request",
    "validation_request",
    "public_fact_query",
    "memory_request",
    "memory_write",
    "rag_query",
    "unknown",
]
TaskType = Literal["none", "readonly_analysis", "artifact_generation", "filesystem_write", "file_modification", "project_generation", "artifact_build", "patch_request", "validation", "memory_curation"]
ActorType = Literal["user", "self", "system", "workspace", "unknown"]
OperationType = Literal["explain", "list", "analyze", "create", "modify", "fix", "validate", "summarize", "search", "remember", "unknown"]
CanonicalOperationType = Literal[
    "conversation", "public_fact_query", "web_search_required", "readonly_analysis",
    "project_analysis", "report_generation", "filesystem_create_directory",
    "filesystem_write_file", "filesystem_append_file", "filesystem_modify_file",
    "filesystem_read_file", "artifact_generation", "artifact_zip_generate",
    "artifact_validate", "patch_preview", "patch_apply", "shell_preview",
    "shell_execute", "test_run", "build_run", "project_generation",
    "android_project_create", "android_apk_build", "validation", "evidence_check",
    "memory_curation", "unknown",
]
ObjectType = Literal["architecture", "capabilities", "memory", "code", "report", "artifact", "project", "model", "unknown"]
OutputChannel = Literal["chat", "artifact", "patch", "task_report", "unknown"]
OutputFormat = Literal["text", "markdown", "json", "file", "unknown"]


class IntentSummary(AIpinhoModel):
    intent_type: IntentType | Literal["readonly_analysis", "artifact_generation", "filesystem_write_request", "file_modification_request", "project_generation_request", "android_project_generation", "artifact_build_request", "patch_request", "public_fact_query", "memory_write", "rag_query", "unknown", "conversation"] = "unknown"
    requires_task: bool = False
    requires_workspace: bool = False
    risk_level: RiskLevel = "low"
    confidence: float = 0.0
    evidence: list[IntentEvidence] = Field(default_factory=list)


class OutputIntent(AIpinhoModel):
    channel: OutputChannel = "unknown"
    format: OutputFormat = "unknown"
    should_save_file: bool = False


class IntentMap(AIpinhoModel):
    intent_id: str
    raw_prompt: str
    normalized_prompt: str
    language: str = "pt-BR"
    intent_type: IntentType = "unknown"
    task_type: TaskType = "none"
    requires_task: bool = False
    requires_workspace: bool = False
    requires_approval: bool = False
    requested_actions: list[str] = Field(default_factory=list)
    actor: ActorType = "unknown"
    operation: OperationType = "unknown"
    operation_type: CanonicalOperationType = "unknown"
    object: ObjectType = "unknown"
    target: TargetReference = Field(default_factory=TargetReference)
    output_intent: OutputIntent = Field(default_factory=OutputIntent)
    workspace: WorkspaceResolution = Field(default_factory=WorkspaceResolution)
    risk: RiskResult = Field(default_factory=RiskResult)
    ambiguity: AmbiguityResult = Field(default_factory=AmbiguityResult)
    confidence: float = 0.0
    evidence: list[IntentEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[PolicyTraceItem] = Field(default_factory=list)
    segments: list[PromptSegment] = Field(default_factory=list)
    workspace_references: list[WorkspaceReference] = Field(default_factory=list)
    requested_deliverables: list[str] = Field(default_factory=list)
    semantic_intent_graph: SemanticIntentGraph = Field(default_factory=SemanticIntentGraph)

    def to_policy_intent_summary(self) -> IntentSummary:
        policy_intent_type = self.intent_type
        if policy_intent_type == "self_analysis" or policy_intent_type == "capability_explanation" or policy_intent_type == "in_chat_final_report":
            policy_intent_type = "conversation"
        return IntentSummary(
            intent_type=policy_intent_type,
            requires_task=self.requires_task,
            requires_workspace=self.requires_workspace,
            risk_level=self.risk.level,
            confidence=self.confidence,
            evidence=self.evidence,
        )
