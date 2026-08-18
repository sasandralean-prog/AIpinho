from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft
from aipinho.schemas.tasks.task_preview import TaskPreview
from aipinho.schemas.tasks.task_preview_event import TaskPreviewEvent
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.executable_plan_service import ExecutablePlanService
from aipinho.services.orchestration.task_lifecycle_service import TaskLifecycleService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file


def _dump_model(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


class TaskPreviewService:
    def __init__(
        self,
        store: TaskPreviewStore | None = None,
        draft_store: TaskDraftStore | None = None,
        lifecycle: TaskLifecycleService | None = None,
    ) -> None:
        self.store = store or TaskPreviewStore()
        self.draft_store = draft_store or TaskDraftStore()
        self.lifecycle = lifecycle or TaskLifecycleService()
        self.executable_plans = ExecutablePlanService()
        self.preview_policy = load_yaml_file(PATHS.config_root / "policies" / "preview_policy.yaml", critical=True, root=PATHS.config_root / "policies")

    def create_preview_from_draft(self, draft_id: str) -> TaskPreview | None:
        draft = self.draft_store.get(draft_id)
        if draft is None:
            return None
        preview = self._build_preview(draft)
        self.store.save(preview)
        self.append_event(preview.preview_id, "preview_created", f"Preview criado com status {preview.status}.")
        self._update_draft_for_preview(draft, preview)
        return preview

    def get_preview(self, preview_id: str) -> TaskPreview | None:
        return self.store.get(preview_id)

    def list_events(self, preview_id: str) -> list[TaskPreviewEvent]:
        return self.store.list_events(preview_id)

    def refresh_policy(self, preview_id: str) -> TaskPreview | None:
        preview = self.get_preview(preview_id)
        if preview is None:
            return None
        draft = self.draft_store.get(preview.draft_id)
        if draft is None:
            preview.status = "invalid"
            preview.updated_at = utc_now()
            preview.warnings = list(dict.fromkeys([*preview.warnings, "draft_missing_on_refresh"]))
            self.store.save(preview)
            self.append_event(preview.preview_id, "preview_invalidated", "Preview invalidado porque o draft nao existe.")
            return preview
        refreshed = self._build_preview(draft, preview_id=preview.preview_id)
        self.store.save(refreshed)
        self.append_event(refreshed.preview_id, "policy_refreshed", "Policy snapshot do preview foi recalculado.")
        return refreshed

    def append_event(self, preview_id: str, event_type, summary: str, data: dict | None = None) -> TaskPreviewEvent:
        event = TaskPreviewEvent(
            event_id=f"preview_event_{uuid4().hex}",
            preview_id=preview_id,
            event_type=event_type,
            created_at=utc_now(),
            summary=summary,
            data=data or {},
        )
        self.store.append_event(event)
        return event

    def _build_preview(self, draft: TaskContractDraft, preview_id: str | None = None) -> TaskPreview:
        snapshot = self._policy_snapshot(draft)
        status = self._preview_status(draft)
        side_effects = self._side_effects(draft)
        plan = self.executable_plans.validate_draft(draft)
        warnings = list(draft.warnings)
        if status == "approval_required" and not plan["valid"]:
            warnings = list(dict.fromkeys([*warnings, "missing_executable_plan", str(plan["reason_code"])]))
        now = utc_now()
        return TaskPreview(
            preview_id=preview_id or f"preview_{uuid4().hex}",
            draft_id=draft.draft_id,
            session_id=draft.session_id,
            status=status,
            contract_type=draft.contract_type,
            summary=self._summary(draft, status),
            operation_type=draft.operation_type,
            runtime_profile=draft.runtime_profile,
            requested_actions=list(draft.requested_actions),
            allowed_actions=list(draft.allowed_actions),
            denied_actions=list(draft.denied_actions),
            approval_required_for=list(draft.approval_required_for),
            potential_side_effects=side_effects,
            executable_plan_ref=str(plan["executable_plan_ref"]) if plan.get("executable_plan_ref") else draft.executable_plan_ref,
            expected_outcomes=self.executable_plans.expected_outcomes_for(draft),
            safe_to_execute=False,
            safe_to_preview=status in {"preview_ready", "approval_required"},
            policy_snapshot=snapshot,
            trace=list(draft.trace),
            warnings=warnings,
            created_at=now,
            updated_at=now,
        )

    def _preview_status(self, draft: TaskContractDraft):
        if draft.status == "blocked" or draft.workspace.status == "protected":
            return "blocked"
        if draft.status == "needs_clarification" or draft.workspace.status in {"missing", "candidate"}:
            return "needs_clarification"
        if any(action in draft.denied_actions for action in draft.requested_actions):
            if draft.approval_required_for:
                return "approval_required"
            return "blocked"
        if draft.approval_required_for:
            return "approval_required"
        if draft.contract_type not in set(self.preview_policy.get("preview", {}).get("allow_preview_for", [])):
            return "invalid"
        return "preview_ready"

    def _policy_snapshot(self, draft: TaskContractDraft) -> ApprovalPolicySnapshot:
        policy = draft.policy_decision or {}
        trace_hash = hashlib.sha256(json.dumps(draft.trace, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return ApprovalPolicySnapshot(
            policy_decision_id=str(policy.get("decision_id", draft.policy_decision.get("policy_decision_id", "")) or ""),
            policy_status=str(policy.get("status", "unknown")),
            allowed_actions=list(policy.get("allowed_actions", draft.allowed_actions) or []),
            denied_actions=list(policy.get("denied_actions", draft.denied_actions) or []),
            approval_required_for=list(policy.get("approval_required_for", draft.approval_required_for) or []),
            granted_capabilities=list(policy.get("granted_capabilities", []) or []),
            denied_capabilities=list(policy.get("denied_capabilities", []) or []),
            workspace_status=draft.workspace.status,
            risk_level=str(draft.intent_map.get("risk", "unknown")),
            trace_hash=trace_hash,
            config_versions={"preview_policy_schema_version": self.preview_policy.get("schema_version", 1)},
        )

    def _side_effects(self, draft: TaskContractDraft) -> list[str]:
        descriptions = self.preview_policy.get("side_effect_descriptions", {})
        if not isinstance(descriptions, dict):
            descriptions = {}
        result: list[str] = []
        for action in draft.requested_actions:
            if action in descriptions:
                result.append(f"{action}: {descriptions[action]}")
        return result

    def _summary(self, draft: TaskContractDraft, status: str) -> str:
        return f"Preview {status} para contrato {draft.contract_type}. Nenhuma execucao sera realizada nesta sprint."

    def _update_draft_for_preview(self, draft: TaskContractDraft, preview: TaskPreview) -> None:
        target = self.lifecycle.next_for_preview(preview.status)
        if self.lifecycle.can_transition(draft.status, target):
            draft.status = target  # type: ignore[assignment]
            draft.updated_at = utc_now()
            self.draft_store.save(draft)

    def status(self) -> dict[str, object]:
        store_status = self.store.status()
        return {"status": store_status.get("status", "degraded"), "service": "task_preview", "store": store_status, "execution_enabled": False}
