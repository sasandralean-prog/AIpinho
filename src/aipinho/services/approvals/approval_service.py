from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from aipinho.schemas.approvals.approval_decision import ApprovalDecision
from aipinho.schemas.approvals.approval_event import ApprovalEvent
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.approvals.universal_approver import ApprovalOrigin, ApprovalSignature
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_lifecycle_service import ApprovalLifecycleService
from aipinho.services.approvals.approval_policy import ApprovalPolicy
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.approvals.approval_trace import ApprovalTrace
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.executable_plan_service import ExecutablePlanService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.session.session_store import utc_now


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


def snapshot_hash(snapshot: Any) -> str:
    return hashlib.sha256(json.dumps(_dump_model(snapshot), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class ApprovalService:
    def __init__(
        self,
        store: ApprovalStore | None = None,
        preview_service: TaskPreviewService | None = None,
        draft_store: TaskDraftStore | None = None,
        policy: ApprovalPolicy | None = None,
        lifecycle: ApprovalLifecycleService | None = None,
        trace: ApprovalTrace | None = None,
    ) -> None:
        self.store = store or ApprovalStore()
        self.preview_service = preview_service or TaskPreviewService()
        self.draft_store = draft_store or TaskDraftStore()
        self.policy = policy or ApprovalPolicy().load()
        self.lifecycle = lifecycle or ApprovalLifecycleService()
        self.trace = trace or ApprovalTrace()
        self.executable_plans = ExecutablePlanService()

    def create_approval_for_preview(self, preview_id: str, actions: list[str] | None = None, actor: Actor | None = None, reason: str = "") -> ApprovalRequest:
        preview = self.preview_service.get_preview(preview_id)
        if preview is None:
            raise ValueError("preview_not_found")
        if preview.status != "approval_required":
            raise ValueError("preview_does_not_require_approval")
        if preview.policy_snapshot.workspace_status == "protected" or preview.status == "blocked":
            raise ValueError("forbidden_root_or_blocked_preview")
        requested = actions or list(preview.approval_required_for)
        ok, reason_code = self.policy.can_request_actions(requested, preview.approval_required_for, preview.denied_actions)
        if not ok:
            raise ValueError(reason_code)
        if self.policy.require_policy_snapshot() and not preview.policy_snapshot.trace_hash:
            raise ValueError("missing_policy_snapshot")
        draft = self.draft_store.get(preview.draft_id)
        plan = self.executable_plans.validate_draft(draft)
        if not plan["valid"]:
            self.append_event(
                f"approval_blocked_{uuid4().hex}",
                "approval_not_created_no_executable_plan",
                "ApprovalRequest nao foi criado porque o preview nao contem plano executavel.",
                {"preview_id": preview.preview_id, "draft_id": preview.draft_id, "reason_code": plan["reason_code"]},
            )
            raise ValueError(str(plan["reason_code"] or "missing_executable_plan"))
        now = datetime.now(timezone.utc)
        expected_outcomes = self.executable_plans.expected_outcomes_for(draft, plan)
        intent = getattr(draft, "intent_map", {}) if isinstance(getattr(draft, "intent_map", {}), dict) else {}
        execution_intent = intent.get("execution_intent") if isinstance(intent.get("execution_intent"), dict) else {}
        executable_patch_plan = intent.get("executable_patch_plan") if isinstance(intent.get("executable_patch_plan"), dict) else {}
        execution_preview = intent.get("execution_preview") if isinstance(intent.get("execution_preview"), dict) else {}
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=preview.preview_id,
            draft_id=preview.draft_id,
            session_id=preview.session_id,
            workspace_path=draft.workspace.path if draft is not None else None,
            operation_type=draft.operation_type if draft is not None else preview.contract_type,
            contract_type=draft.contract_type if draft is not None else preview.contract_type,
            runtime_profile=draft.runtime_profile if draft is not None else preview.runtime_profile,
            target_paths=self._target_paths(draft, preview),
            expected_outcomes=expected_outcomes,
            executable_plan_ref=str(plan["executable_plan_ref"]),
            execution_id=str(plan["executable_plan_ref"]),
            execution_plan_snapshot={
                "execution_id": str(plan["executable_plan_ref"]),
                "source": "canonical_executable_plan_service" if executable_patch_plan else "legacy_executable_plan_service",
                "valid": bool(plan.get("valid")),
                "reason_code": plan.get("reason_code"),
                "plan_kind": plan.get("plan_kind"),
                "execution_intent": execution_intent,
                "executable_patch_plan": executable_patch_plan,
                "execution_preview": execution_preview,
            },
            preview_hash=snapshot_hash(preview),
            policy_snapshot_hash=snapshot_hash(preview.policy_snapshot),
            preview={
                "available": True,
                "summary": preview.summary,
                "diff_ref": None,
                "content_preview_ref": preview.preview_id,
                "executable_plan_ref": str(plan["executable_plan_ref"]),
                "execution_id": str(plan["executable_plan_ref"]),
                "expected_outcomes": expected_outcomes,
            },
            policy_refs=[preview.policy_snapshot.policy_decision_id] if preview.policy_snapshot.policy_decision_id else [],
            allowed_by_policy=True,
            forbidden_operations=list(preview.denied_actions),
            status="pending",
            actions_requested=requested,
            approval_scope="future_execution",
            reason=reason,
            risk_level=preview.policy_snapshot.risk_level,
            policy_snapshot=preview.policy_snapshot,
            expires_at=(now + timedelta(minutes=self.policy.ttl_minutes())).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=actor or Actor(type="system", id="approval_service"),
            trace=[self.trace.item(stage="approval_create", decision="pending", reason="approval_created_without_execution", source="services/approvals/approval_service.py")],
            execution_status="not_executed",
        )
        self.store.save(approval)
        self.append_event(
            approval.approval_id,
            "approval_created",
            "ApprovalRequest criado; nenhuma execucao realizada.",
            {
                "preview_id": approval.preview_id,
                "workspace_path": approval.workspace_path,
                "operation_type": approval.operation_type,
                "target_paths": approval.target_paths,
                "executable_plan_ref": approval.executable_plan_ref,
                "expected_outcomes": approval.expected_outcomes,
                "actions_requested": approval.actions_requested,
                "risk_level": approval.risk_level,
            },
        )
        self.append_event(
            approval.approval_id,
            "approval_preview_created",
            "Preview associado ao ApprovalRequest; side effects continuam pausados.",
            {
                "preview_id": approval.preview_id,
                "run_id": approval.run_id,
                "task_id": approval.task_id,
                "operation_type": approval.operation_type,
                "target_paths": approval.target_paths,
                "executable_plan_ref": approval.executable_plan_ref,
                "expected_outcomes": approval.expected_outcomes,
                "source_paths": [],
                "commands": approval.commands,
                "risk_level": approval.risk_level,
                "status": approval.status,
                "policy_refs": approval.policy_refs,
                "evidence_refs": [{"type": "preview", "ref_id": approval.preview_id}],
            },
        )
        self._update_draft_status(approval.draft_id, "approval_pending")
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        approval = self.store.get(approval_id)
        return self._reconcile_expiration(approval)

    def list_approvals(self, *, status: str | None = None, session_id: str | None = None, limit: int = 100) -> list[ApprovalRequest]:
        candidates = self.store.list(status=None, session_id=session_id, limit=limit)
        approvals = [
            approval
            for item in candidates
            if (approval := self._reconcile_expiration(item)) is not None
            and (status is None or approval.status == status)
        ]
        return approvals[: max(0, limit)]

    def list_for_task(self, task_id: str, *, status: str | None = None, limit: int = 100) -> list[ApprovalRequest]:
        approvals = [
            approval
            for approval in self.list_approvals(status=status, limit=1000)
            if approval.run_id == task_id or approval.task_id == task_id
        ]
        return approvals[: max(1, min(limit, 500))]

    def attach_runtime_context(
        self,
        approval_id: str,
        *,
        run_id: str,
        task_id: str | None = None,
        workspace_path: str | None = None,
        execution_plan: dict[str, Any] | None = None,
    ) -> ApprovalRequest | None:
        approval = self.get_approval(approval_id)
        if approval is None:
            return None
        approval.run_id = run_id
        approval.task_id = task_id or approval.task_id
        if workspace_path and not approval.workspace_path:
            approval.workspace_path = workspace_path
        if execution_plan:
            execution_id = str(execution_plan.get("execution_id") or "")
            if execution_id:
                approval.execution_id = execution_id
                approval.executable_plan_ref = approval.executable_plan_ref or execution_id
                approval.execution_plan_snapshot = dict(execution_plan)
                approval.preview.setdefault("execution_id", execution_id)
                approval.preview.setdefault("execution_plan_ref", execution_id)
        approval.updated_at = utc_now()
        self.store.save(approval)
        self.append_event(
            approval.approval_id,
            "approval_runtime_context_attached",
            "Approval vinculado a uma TaskRun resumivel.",
            {
                "run_id": run_id,
                "task_id": approval.task_id,
                "workspace_path": approval.workspace_path,
                "execution_id": approval.execution_id,
            },
        )
        return approval

    def _reconcile_expiration(self, approval: ApprovalRequest | None) -> ApprovalRequest | None:
        if approval is None or approval.status != "pending" or not self.lifecycle.is_expired(approval.expires_at):
            return approval
        approval.status = "expired"
        approval.updated_at = utc_now()
        self.store.save(approval)
        self.append_event(approval.approval_id, "approval_expired", "Approval expirou antes da decisao.")
        return approval

    def approve(
        self,
        approval_id: str,
        actor: Actor | None = None,
        reason: str = "",
        scope: str = "single_action",
        approval_origin: ApprovalOrigin | None = None,
        approval_signature: ApprovalSignature | None = None,
    ) -> tuple[ApprovalDecision, ApprovalRequest]:
        return self._decide(
            approval_id,
            "approved",
            actor=actor,
            reason=reason,
            scope=scope,
            approval_origin=approval_origin,
            approval_signature=approval_signature,
        )

    def reject(
        self,
        approval_id: str,
        actor: Actor | None = None,
        reason: str = "",
        scope: str = "single_action",
        approval_origin: ApprovalOrigin | None = None,
        approval_signature: ApprovalSignature | None = None,
    ) -> tuple[ApprovalDecision, ApprovalRequest]:
        return self._decide(
            approval_id,
            "rejected",
            actor=actor,
            reason=reason,
            scope=scope,
            approval_origin=approval_origin,
            approval_signature=approval_signature,
        )

    def cancel(self, approval_id: str, actor: Actor | None = None, reason: str = "", scope: str = "single_action") -> tuple[ApprovalDecision, ApprovalRequest]:
        return self._decide(approval_id, "cancelled", actor=actor, reason=reason, scope=scope)

    def approve_batch(self, approval_ids: list[str], actor: Actor | None = None, reason: str = "", *, safe_only: bool = False) -> list[tuple[ApprovalDecision, ApprovalRequest]]:
        return self._decide_batch(approval_ids, "approved", actor=actor, reason=reason, scope="safe_batch" if safe_only else "selected_actions", safe_only=safe_only)

    def reject_batch(self, approval_ids: list[str], actor: Actor | None = None, reason: str = "", *, safe_only: bool = False) -> list[tuple[ApprovalDecision, ApprovalRequest]]:
        return self._decide_batch(approval_ids, "rejected", actor=actor, reason=reason, scope="safe_batch" if safe_only else "selected_actions", safe_only=safe_only)

    def safe_batch_for_task(self, task_id: str) -> list[ApprovalRequest]:
        return [approval for approval in self.list_for_task(task_id, status="pending", limit=500) if self._safe_batch_allowed(approval)]

    def _decide_batch(self, approval_ids: list[str], decision_value: str, actor: Actor | None = None, reason: str = "", *, scope: str, safe_only: bool) -> list[tuple[ApprovalDecision, ApprovalRequest]]:
        unique_ids = [item for item in dict.fromkeys(str(value).strip() for value in approval_ids) if item]
        if not unique_ids:
            raise ValueError("no_approvals_selected")
        approvals = [self.get_approval(approval_id) for approval_id in unique_ids]
        if any(approval is None for approval in approvals):
            raise ValueError("approval_not_found")
        real = [approval for approval in approvals if approval is not None]
        task_ids = {approval.task_id or approval.run_id or "" for approval in real}
        workspaces = {approval.workspace_path or approval.workspace_id or "" for approval in real}
        if len(task_ids - {""}) > 1:
            raise ValueError("batch_cross_task_not_allowed")
        if len(workspaces - {""}) > 1:
            raise ValueError("batch_cross_workspace_not_allowed")
        if safe_only and any(not self._safe_batch_allowed(approval) for approval in real):
            raise ValueError("batch_contains_non_safe_action")
        results = [
            self._decide(approval.approval_id, decision_value, actor=actor, reason=reason, scope=scope)
            for approval in real
        ]
        batch_event = "approval_batch_approved" if decision_value == "approved" else "approval_batch_denied"
        for _decision, approval in results:
            self.append_event(
                approval.approval_id,
                batch_event,
                "Decisao em lote registrada para approval governado.",
                {
                    "scope": scope,
                    "safe_only": safe_only,
                    "run_id": approval.run_id,
                    "task_id": approval.task_id,
                    "operation_type": approval.operation_type,
                    "target_paths": approval.target_paths,
                    "source_paths": [],
                    "commands": approval.commands,
                    "risk_level": approval.risk_level,
                    "status": approval.status,
                    "policy_refs": approval.policy_refs,
                    "evidence_refs": [{"type": "approval", "ref_id": approval.approval_id}],
                },
            )
        return results

    def _decide(
        self,
        approval_id: str,
        decision_value: str,
        actor: Actor | None = None,
        reason: str = "",
        scope: str = "single_action",
        approval_origin: ApprovalOrigin | None = None,
        approval_signature: ApprovalSignature | None = None,
    ) -> tuple[ApprovalDecision, ApprovalRequest]:
        approval = self.get_approval(approval_id)
        if approval is None:
            raise ValueError("approval_not_found")
        ok, reason_code = self.lifecycle.ensure_pending(approval.status)
        if not ok:
            raise ValueError(reason_code)
        if self.lifecycle.is_expired(approval.expires_at):
            approval.status = "expired"
            approval.updated_at = utc_now()
            self.store.save(approval)
            self.append_event(approval.approval_id, "approval_expired", "Approval expirou antes da decisao.")
            raise ValueError("approval_expired")
        if not self.lifecycle.can_transition(approval.status, decision_value):
            raise ValueError("invalid_approval_transition")
        approval.status = decision_value  # type: ignore[assignment]
        approval.updated_at = utc_now()
        approval.execution_status = "not_executed"
        approval.approval_origin = approval_origin
        approval.approval_signature = approval_signature
        approval.approval_authority = "AIpinho"
        decision = ApprovalDecision(
            approval_id=approval.approval_id,
            decision=decision_value,  # type: ignore[arg-type]
            actor=actor or Actor(type="user", id="local_user"),
            reason=reason,
            scope=scope,
            decided_at=approval.updated_at,
            policy_snapshot_hash=snapshot_hash(approval.policy_snapshot),
            approval_origin=approval_origin,
            approval_signature=approval_signature,
            approval_authority="AIpinho",
            trace=[self.trace.item(stage="approval_decision", decision=decision_value, reason="decision_recorded_without_execution", source="services/approvals/approval_service.py")],
            execution_status="not_executed",
        )
        self.store.save(approval)
        event_type = {"approved": "approval_approved", "rejected": "approval_rejected", "cancelled": "approval_cancelled"}[decision_value]
        self.append_event(
            approval.approval_id,
            event_type,
            f"Approval {decision_value}; execucao sera retomada apenas pelo runtime governado quando aplicavel.",
            {
                "scope": scope,
                "run_id": approval.run_id,
                "task_id": approval.task_id,
                "approval_origin": approval_origin.model_dump() if approval_origin else None,
                "approval_signature": approval_signature.model_dump() if approval_signature else None,
                "approval_authority": "AIpinho",
            },
        )
        if approval.approval_scope == "future_artifact_write":
            try:
                from aipinho.services.artifacts.artifact_approval_bridge import ArtifactApprovalBridge
                ArtifactApprovalBridge(approval_store=self.store).record_approval_decision(approval)
            except Exception:
                self.append_event(approval.approval_id, "artifact_preview_sync_failed", "Artifact preview sync failed; approval still did not execute a write.")
        draft_target = {"approved": "approved_for_future_execution", "rejected": "rejected", "cancelled": "cancelled"}[decision_value]
        self._update_draft_status(approval.draft_id, draft_target)
        return decision, approval

    def refresh_policy(self, approval_id: str) -> ApprovalRequest | None:
        approval = self.get_approval(approval_id)
        if approval is None:
            return None
        preview = self.preview_service.refresh_policy(approval.preview_id)
        if preview is None or snapshot_hash(preview.policy_snapshot) != snapshot_hash(approval.policy_snapshot):
            if approval.status == "pending":
                approval.status = "invalidated_by_policy_change"
                approval.updated_at = utc_now()
                self.store.save(approval)
                self.append_event(approval.approval_id, "approval_invalidated", "Approval invalidado por mudanca de policy snapshot.")
                self._update_draft_status(approval.draft_id, "invalidated_by_policy_change")
        else:
            self.append_event(approval.approval_id, "policy_refreshed", "Policy refresh sem mudanca relevante.")
        return approval

    def append_event(self, approval_id: str, event_type, summary: str, data: dict | None = None) -> ApprovalEvent:
        event = ApprovalEvent(
            event_id=f"approval_event_{uuid4().hex}",
            approval_id=approval_id,
            event_type=event_type,
            created_at=utc_now(),
            summary=summary,
            data=data or {},
        )
        self.store.append_event(event)
        return event

    def list_events(self, approval_id: str) -> list[ApprovalEvent]:
        return self.store.list_events(approval_id)

    def _update_draft_status(self, draft_id: str, status: str) -> None:
        draft = self.draft_store.get(draft_id)
        if draft is None:
            return
        draft.status = status  # type: ignore[assignment]
        draft.updated_at = utc_now()
        draft.safe_to_execute = False
        self.draft_store.save(draft)

    def _safe_batch_allowed(self, approval: ApprovalRequest) -> bool:
        excluded = self.policy.safe_batch_excluded_actions() or {
            "delete_file",
            "delete_files",
            "move_file",
            "move_files",
            "git_commit",
            "git_push",
            "destructive_shell",
            "network_shell",
            "process_control_shell",
            "run_command",
        }
        actions = set(approval.actions_requested)
        if not actions:
            return False
        if actions.intersection(excluded):
            return False
        if approval.policy_snapshot.denied_actions and actions.intersection(set(approval.policy_snapshot.denied_actions)):
            return False
        return approval.status == "pending" and approval.allowed_by_policy

    @staticmethod
    def _target_paths(draft, preview) -> list[str]:
        return ExecutablePlanService().real_target_paths(draft, preview)

    def status(self) -> dict[str, object]:
        policy_status = self.policy.status()
        store_status = self.store.status()
        overall = "ok" if policy_status.get("status") == store_status.get("status") == "ok" else "degraded"
        runtime = self.policy.config.get("runtime_execution", {})
        execution_enabled = bool(
            isinstance(runtime, dict)
            and runtime.get("approved_side_effect_execution_enabled", False)
            and runtime.get("resume_after_approval", False)
        )
        return {"status": overall, "service": "approval", "policy": policy_status, "store": store_status, "execution_enabled": execution_enabled}
