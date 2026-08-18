from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def prefixed_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class ReplaySnapshotMetadata(AIpinhoModel):
    snapshot_id: str = Field(default_factory=lambda: prefixed_id("replay_snapshot"))
    capture_reason: str
    system_version: str = "aipinho-v1"
    policy_hashes: dict[str, str] = Field(default_factory=dict)
    config_hashes: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    sanitized: bool = False


class ReplayInputBundle(AIpinhoModel):
    prompt: str | None = None
    task_id: str | None = None
    trace_id: str | None = None
    event_id: str | None = None
    session_id: str | None = None
    maintenance_run_id: str | None = None
    skill_trace_id: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class ReplayDecisionBundle(AIpinhoModel):
    intent_map: dict[str, Any] = Field(default_factory=dict)
    task_contract: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    capability_decision: dict[str, Any] = Field(default_factory=dict)
    approval_state: dict[str, Any] = Field(default_factory=dict)


class ReplayContextBundleRef(AIpinhoModel):
    context_bundle_id: str | None = None
    context_trace_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)


class ReplayEventTimeline(AIpinhoModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


class ReplayModelRunRef(AIpinhoModel):
    model_id: str | None = None
    provider_id: str | None = None
    real_inference: bool = False


class ReplayRagResultRef(AIpinhoModel):
    result_id: str | None = None
    citations: list[str] = Field(default_factory=list)


class ReplayMemoryUsageRef(AIpinhoModel):
    memory_ids: list[str] = Field(default_factory=list)
    memory_write: bool = False


class ReplaySkillTraceRef(AIpinhoModel):
    skill_trace_id: str | None = None
    side_effects_allowed: bool = False


class ReplayMaintenanceRef(AIpinhoModel):
    maintenance_run_id: str | None = None
    autonomous_apply: bool = False


class ReplayArtifactRef(AIpinhoModel):
    artifact_id: str | None = None
    raw_path_download_allowed: bool = False


class ReplayValidationRef(AIpinhoModel):
    validation_id: str | None = None
    executed: bool = False


class ReplaySpeakerRef(AIpinhoModel):
    message_id: str | None = None
    claims_real_completion: bool = False


class ReplaySanitizationResult(AIpinhoModel):
    sanitized: bool
    blocked: bool = False
    redactions: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ReplaySnapshot(AIpinhoModel):
    metadata: ReplaySnapshotMetadata
    input_bundle: ReplayInputBundle = Field(default_factory=ReplayInputBundle)
    decision_bundle: ReplayDecisionBundle = Field(default_factory=ReplayDecisionBundle)
    context_ref: ReplayContextBundleRef = Field(default_factory=ReplayContextBundleRef)
    event_timeline: ReplayEventTimeline = Field(default_factory=ReplayEventTimeline)
    model_run_ref: ReplayModelRunRef = Field(default_factory=ReplayModelRunRef)
    rag_result_ref: ReplayRagResultRef = Field(default_factory=ReplayRagResultRef)
    memory_usage_ref: ReplayMemoryUsageRef = Field(default_factory=ReplayMemoryUsageRef)
    skill_trace_ref: ReplaySkillTraceRef = Field(default_factory=ReplaySkillTraceRef)
    maintenance_ref: ReplayMaintenanceRef = Field(default_factory=ReplayMaintenanceRef)
    artifact_ref: ReplayArtifactRef = Field(default_factory=ReplayArtifactRef)
    validation_ref: ReplayValidationRef = Field(default_factory=ReplayValidationRef)
    speaker_ref: ReplaySpeakerRef = Field(default_factory=ReplaySpeakerRef)
    sanitization: ReplaySanitizationResult = Field(default_factory=lambda: ReplaySanitizationResult(sanitized=False))


class ReplayCaptureRequest(AIpinhoModel):
    task_id: str | None = None
    trace_id: str | None = None
    event_id: str | None = None
    session_id: str | None = None
    maintenance_run_id: str | None = None
    skill_trace_id: str | None = None
    reason: str
    prompt: str | None = None
    snapshot_payload: dict[str, Any] = Field(default_factory=dict)


class ReplayCaptureResult(AIpinhoModel):
    status: str
    snapshot: ReplaySnapshot | None = None
    reasons: list[str] = Field(default_factory=list)


class ReplayCase(AIpinhoModel):
    case_id: str = Field(default_factory=lambda: prefixed_id("replay_case"))
    snapshot_id: str
    title: str
    category: str = "general"
    golden_expectations: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "enabled"
    created_at: str = Field(default_factory=utc_now_iso)


class ReplayRun(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: prefixed_id("replay_run"))
    case_id: str
    snapshot_id: str
    status: str = "completed"
    dry_run: bool = True
    side_effects_performed: bool = False
    model_real_inference: bool = False
    shell_executed: bool = False
    git_executed: bool = False
    patch_apply_executed: bool = False
    external_network_called: bool = False
    memory_write: bool = False
    workspace_mutation: bool = False
    result_payload: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)


class ReplayRunResult(AIpinhoModel):
    status: str
    run: ReplayRun


class ReplayDiff(AIpinhoModel):
    diff_id: str = Field(default_factory=lambda: prefixed_id("replay_diff"))
    run_id: str
    differences: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "no_diff"


class ReplayTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: prefixed_id("replay_trace"))
    run_id: str | None = None
    snapshot_id: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class ReplayAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: prefixed_id("replay_audit"))
    action: str
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)


class ReplayStatus(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    side_effects_allowed: bool = False
    model_real_inference_allowed: bool = False
    shell_allowed: bool = False
    git_allowed: bool = False
    patch_apply_allowed: bool = False
    external_network_allowed: bool = False
    memory_write_allowed: bool = False
