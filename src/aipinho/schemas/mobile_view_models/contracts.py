from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ScreenName = Literal["dashboard", "chat", "pipeline", "debugger", "config"]
SafetyAnswer = Literal["safe", "caution", "risky", "blocked", "unknown"]
Severity = Literal["info", "success", "warning", "danger", "blocked", "unknown"]
CardStatus = Literal["healthy", "degraded", "offline", "blocked", "pending", "running", "completed", "failed", "historical", "unknown"]
ActionKind = Literal[
    "navigate",
    "copy",
    "refresh",
    "retry",
    "restart_port",
    "restart_backend",
    "restart_monitor_via_bootstrap",
    "open_trace",
    "open_raw_viewer",
    "open_artifact",
    "create_support_bundle",
    "request_approval",
    "cancel_run",
]
RiskLevel = Literal["low", "medium", "high", "critical"]
PresentationMode = Literal["normal", "details", "raw_debug"]
EvidenceType = Literal[
    "event",
    "trace",
    "context_bundle",
    "validation",
    "rag_citation",
    "memory_evidence",
    "policy_decision",
    "task_run",
    "artifact",
    "model_run",
    "skill_trace",
    "maintenance_run",
    "replay_run",
    "monitor",
    "approval",
    "patch_plan",
    "ocr_run",
    "vision_run",
]


class SafetyState(AIpinhoModel):
    answer: SafetyAnswer
    reason: str


class EvidenceRef(AIpinhoModel):
    type: EvidenceType
    ref_id: str
    human_label: str
    sanitized: bool = True


class HumanizedAnswerSet(AIpinhoModel):
    what_is_happening: str
    why_is_it_happening: str
    is_it_safe: SafetyState
    what_can_i_do_now: list[str] = Field(default_factory=list)
    what_evidence_supports_this: list[EvidenceRef] = Field(default_factory=list)
    can_copy_sanitized_summary: bool = True


class HumanizedMetadata(AIpinhoModel):
    values: dict[str, str] = Field(default_factory=dict)


class SafeUiAction(AIpinhoModel):
    action_id: str
    label: str
    kind: ActionKind
    risk: RiskLevel = "low"
    requires_confirmation: bool = False
    requires_approval: bool = False
    enabled: bool = True
    disabled_reason: str | None = None
    endpoint_ref: str
    method: Literal["GET", "POST"] = "GET"
    side_effect: bool = False
    human_explanation: str


class SanitizedCopyPayload(AIpinhoModel):
    card_id: str
    summary: str
    metadata: dict[str, str] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    copy_policy: Literal["sanitized_only", "raw_ref_only", "blocked"] = "sanitized_only"
    contains_secret: bool = False


class RawViewerRef(AIpinhoModel):
    raw_ref: str
    copy_endpoint: str
    viewer_endpoint: str
    policy: Literal["sanitized_only", "blocked"] = "sanitized_only"


class HumanizedCard(AIpinhoModel):
    card_id: str
    screen: ScreenName
    card_type: str
    title: str
    severity: Severity = "info"
    status: CardStatus = "unknown"
    answers: HumanizedAnswerSet
    metadata: dict[str, object] = Field(default_factory=dict)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    safe_actions: list[SafeUiAction] = Field(default_factory=list)
    copy_payload: dict[str, object] = Field(default_factory=lambda: {
        "summary_available": True,
        "raw_available": False,
        "copy_policy": "sanitized_only",
    }, alias="copy")
    raw_ref: str | None = None
    trace_id: str | None = None
    event_ids: list[str] = Field(default_factory=list)


class MobileScreenState(AIpinhoModel):
    screen: ScreenName
    status: CardStatus
    human_summary: str
    warnings: list[str] = Field(default_factory=list)
    raw_default_visible: bool = False
    ui_decides_policy: bool = False
    ui_decides_safety: bool = False
    ui_decides_final_status: bool = False


class MobileScreen(AIpinhoModel):
    state: MobileScreenState
    cards: list[HumanizedCard] = Field(default_factory=list)
    trace_id: str | None = None


class EvidenceBundleView(AIpinhoModel):
    evidence_type: str
    ref_id: str
    status: CardStatus = "unknown"
    cards: list[HumanizedCard] = Field(default_factory=list)
    sanitized: bool = True


class MobileSupportBundlePreview(AIpinhoModel):
    status: CardStatus = "pending"
    cards: list[HumanizedCard] = Field(default_factory=list)
    artifact_preview: dict[str, str] = Field(default_factory=dict)
    sanitized: bool = True
    side_effect: bool = False


class MobileViewModelTrace(AIpinhoModel):
    trace_id: str
    source_endpoints: list[str] = Field(default_factory=list)
    adapters_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChatPresentationArtifact(AIpinhoModel):
    artifact_id: str | None = None
    filename: str
    content_type: str
    size_bytes: int | None = None
    download_endpoint: str | None = None
    label: str = "Baixar artifact"
    requires_token: bool = True
    status: str = "ready"


class ChatPresentationMessage(AIpinhoModel):
    message_id: str
    role: str
    label: str
    text: str
    created_at: str | None = None
    status: str = "completed"
    task_id: str | None = None
    safety_label: str = "Seguro"
    copy_available: bool = True
    artifacts: list[ChatPresentationArtifact] = Field(default_factory=list)


class ChatPresentationDetail(AIpinhoModel):
    label: str
    value: str
    severity: Severity = "info"


class MobileChatPresentation(AIpinhoModel):
    mode: PresentationMode = "normal"
    messages: list[ChatPresentationMessage] = Field(default_factory=list)
    state_lines: list[str] = Field(default_factory=list)
    details: list[ChatPresentationDetail] = Field(default_factory=list)
    raw_available: bool = False
    raw_default_visible: bool = False
    empty_state: str | None = None


class MobileDashboardViewModel(MobileScreen):
    pass


class MobileChatViewModel(MobileScreen):
    session_id: str | None = None
    presentation: MobileChatPresentation = Field(default_factory=MobileChatPresentation)


class MobileTaskQueueSummary(AIpinhoModel):
    total: int = 0
    active: int = 0
    pending: int = 0
    requires_decision: int = 0
    max_pending: int = 0
    selected_task_id: str | None = None
    selected_approval_id: str | None = None
    approval_kind: str | None = None
    linked_task_run_id: str | None = None
    task_approvals_pending: int = 0
    standalone_approvals_pending: int = 0


class MobilePipelineViewModel(MobileScreen):
    task_id: str | None = None
    selected_task_id: str | None = None
    selected_approval_id: str | None = None
    approval_kind: str | None = None
    linked_task_run_id: str | None = None
    task_approvals_pending: int = 0
    standalone_approvals_pending: int = 0
    queue: MobileTaskQueueSummary = Field(default_factory=MobileTaskQueueSummary)


class MobileDebuggerViewModel(MobileScreen):
    filters: list[str] = Field(default_factory=list)


class MobileConfigViewModel(MobileScreen):
    capabilities: dict[str, bool] = Field(default_factory=dict)
