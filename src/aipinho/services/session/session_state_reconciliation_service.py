from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.chat.session_state import SessionState
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.session.session_policy_service import SessionPolicyService
from aipinho.services.session.session_store import utc_now


class SessionStateReconciliationService:
    def __init__(
        self,
        *,
        policy: SessionPolicyService | None = None,
        drafts: TaskDraftStore | None = None,
        runs: TaskRunStore | None = None,
        lifecycle: TaskRunLifecycleService | None = None,
    ) -> None:
        self.policy = policy or SessionPolicyService().load()
        self.drafts = drafts or TaskDraftStore()
        self.runs = runs or TaskRunStore()
        self.lifecycle = lifecycle or TaskRunLifecycleService()

    def reconcile(self, state: SessionState) -> tuple[SessionState, list[str]]:
        reasons: list[str] = []
        if self.policy.expire_sessions_on_read() and self._expired(state.expires_at):
            state.status = "expired"
            state.active_task_draft_id = None
            state.updated_at = utc_now()
            return state, ["session_expired"]

        draft_id = state.active_task_draft_id
        if not draft_id:
            return state, reasons

        draft = self.drafts.get(draft_id)
        if draft is None:
            if self.policy.clear_missing_active_task_draft():
                state.active_task_draft_id = None
                state.updated_at = utc_now()
                reasons.append("active_task_draft_missing")
            return state, reasons

        if self._expired(draft.expires_at) or draft.status in self.policy.active_task_draft_terminal_statuses():
            state.active_task_draft_id = None
            state.updated_at = utc_now()
            reasons.append("active_task_draft_terminal_or_expired")
            return state, reasons

        related_runs = self.runs.list_runs(draft_id=draft_id, limit=1000)
        if (
            related_runs
            and self.policy.clear_active_task_draft_when_all_runs_terminal()
            and all(self.lifecycle.is_terminal(run.status) for run in related_runs)
        ):
            state.active_task_draft_id = None
            state.updated_at = utc_now()
            reasons.append("active_task_runs_terminal")
        return state, reasons

    @staticmethod
    def _expired(value: str | None) -> bool:
        if not value:
            return False
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
        except ValueError:
            return False
