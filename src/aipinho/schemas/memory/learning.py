from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


LearningCandidateType = Literal[
    "bug_pattern",
    "fix_pattern",
    "validation_lesson",
    "ux_lesson",
    "policy_lesson",
    "prompt_routing_lesson",
    "quality_gate_lesson",
    "workflow_lesson",
    "command_learning",
    "failure_pattern",
    "template_learning",
    "artifact_learning",
    "skill_pack_learning",
    "project_learning",
]
LearningCandidateStatus = Literal["proposed", "accepted", "rejected", "archived", "stale", "superseded", "blocked", "needs_review"]
LearningConfidence = Literal["low", "medium", "high", "confirmed"]
LearningScope = Literal["project", "skill_pack", "template", "artifact", "command", "regression", "global_guarded"]


class LearningExtractionRequest(AIpinhoModel):
    source_type: str = "run_summary"
    source_id: str | None = None
    agent_id: str = "aipinho"
    session_id: str | None = None
    run_id: str | None = None
    project_id: str | None = None
    skill_pack_id: str | None = None
    template_id: str | None = None
    task_id: str | None = None
    outcome: str | None = None
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    reusable_lessons: list[dict[str, Any] | str] = Field(default_factory=list)
    commands_successful: list[dict[str, Any] | str] = Field(default_factory=list)
    commands_failed: list[dict[str, Any] | str] = Field(default_factory=list)
    validations_run: list[dict[str, Any] | str] = Field(default_factory=list)
    artifacts_created: list[dict[str, Any] | str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class RunLearningSummary(AIpinhoModel):
    run_summary_id: str = Field(default_factory=lambda: f"run_learning_{uuid4().hex}")
    source_type: str
    source_id: str | None = None
    agent_id: str
    session_id: str | None = None
    run_id: str | None = None
    project_id: str | None = None
    skill_pack_id: str | None = None
    template_id: str | None = None
    outcome: str = "unknown"
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    commands_successful: list[str] = Field(default_factory=list)
    commands_failed: list[str] = Field(default_factory=list)
    validations_run: list[str] = Field(default_factory=list)
    artifacts_created: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    blocked_reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemoryCandidateV2(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"learning_candidate_{uuid4().hex}")
    type: LearningCandidateType
    title: str
    summary: str
    reusable_when: list[str] = Field(default_factory=list)
    scope: LearningScope = "regression"
    status: LearningCandidateStatus = "proposed"
    confidence: LearningConfidence = "medium"
    source_type: str = "run_summary"
    source_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    project_id: str | None = None
    skill_pack_id: str | None = None
    template_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    command_refs: list[str] = Field(default_factory=list)
    validation_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    block_reason_codes: list[str] = Field(default_factory=list)
    contains_secret_risk: bool = False
    raw_log_blocked: bool = False
    requires_review: bool = True
    memory_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class MemoryRecord(AIpinhoModel):
    memory_id: str = Field(default_factory=lambda: f"learning_memory_{uuid4().hex}")
    candidate_id: str
    type: LearningCandidateType
    title: str
    summary: str
    reusable_when: list[str] = Field(default_factory=list)
    scope: LearningScope
    status: Literal["approved", "superseded", "archived", "stale"] = "approved"
    confidence: LearningConfidence = "medium"
    evidence_refs: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    project_id: str | None = None
    skill_pack_id: str | None = None
    template_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    accepted_by: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class CommandLearningRecord(AIpinhoModel):
    command_learning_id: str = Field(default_factory=lambda: f"command_learning_{uuid4().hex}")
    command_summary: str
    outcome: str
    evidence_refs: list[str] = Field(default_factory=list)
    project_id: str | None = None
    skill_pack_id: str | None = None


class FailurePatternRecord(AIpinhoModel):
    failure_pattern_id: str = Field(default_factory=lambda: f"failure_pattern_{uuid4().hex}")
    symptom: str
    likely_cause: str = "unknown"
    fix_pattern: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    project_id: str | None = None
    skill_pack_id: str | None = None


class TemplateLearningRecord(AIpinhoModel):
    template_learning_id: str = Field(default_factory=lambda: f"template_learning_{uuid4().hex}")
    template_id: str
    outcome: str
    lesson: str
    evidence_refs: list[str] = Field(default_factory=list)


class ArtifactLearningRecord(AIpinhoModel):
    artifact_learning_id: str = Field(default_factory=lambda: f"artifact_learning_{uuid4().hex}")
    artifact_id: str
    outcome: str
    lesson: str
    evidence_refs: list[str] = Field(default_factory=list)


class ProjectLearningProfile(AIpinhoModel):
    project_id: str
    accepted_memory_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    successful_commands: list[str] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    artifact_lessons: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now_iso)


class SkillPackLearningProfile(AIpinhoModel):
    skill_pack_id: str
    accepted_memory_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    updated_at: str = Field(default_factory=utc_now_iso)


class TemplateLearningProfile(AIpinhoModel):
    template_id: str
    accepted_memory_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    updated_at: str = Field(default_factory=utc_now_iso)


class MemoryReviewQueue(AIpinhoModel):
    status: str = "ok"
    candidates: list[MemoryCandidateV2] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class MemoryQuery(AIpinhoModel):
    query: str | None = None
    type: LearningCandidateType | None = None
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None
    skill_pack_id: str | None = None
    template_id: str | None = None
    confidence: LearningConfidence | None = None
    status: str | None = "approved"
    limit: int = 20


class MemoryReviewRequest(AIpinhoModel):
    reviewed_by: str = "codex"
    reason: str = ""


class LearningExtractionResult(AIpinhoModel):
    extraction_id: str = Field(default_factory=lambda: f"learning_extraction_{uuid4().hex}")
    status: str
    run_summary: RunLearningSummary
    candidates: list[MemoryCandidateV2] = Field(default_factory=list)
    blocked_reason_codes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class LearningStatus(AIpinhoModel):
    status: str
    candidates: int = 0
    accepted_memories: int = 0
    run_summaries: int = 0
    raw_hidden_by_default: bool = True
    secret_storage_blocked: bool = True
    evidence_required: bool = True
