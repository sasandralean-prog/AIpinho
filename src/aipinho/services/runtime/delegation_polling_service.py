from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.runtime.delegation_contract import DelegationContract
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


class DelegationPollingService:
    def __init__(
        self,
        *,
        store: ExternalCollaborationStore | None = None,
        task_store: TaskRunStore | None = None,
        universal_sessions: UniversalTaskSessionService | None = None,
    ) -> None:
        self.store = store or ExternalCollaborationStore()
        self.task_store = task_store or TaskRunStore()
        self.universal_sessions = universal_sessions or UniversalTaskSessionService(store=self.task_store)

    def poll(self, delegation_id: str) -> dict[str, object] | None:
        contract = self.store.get_delegation(delegation_id)
        if contract is None:
            return None
        child = self.universal_sessions.get_session(contract.child_run_id)
        contract.polling_count += 1
        contract.updated_at = utc_now_iso()
        if child is None:
            contract.status = "failed"
            contract.completed_at = contract.completed_at or utc_now_iso()
            self._event(contract.parent_run_id, "delegation_failed", "failed", "Delegation child run not found.", contract)
        elif child.status == "COMPLETED":
            contract.status = "completed"
            contract.completed_at = contract.completed_at or utc_now_iso()
            contract.review_status = "ready_for_review"
            self._event(contract.parent_run_id, "delegation_completed", "completed", "Delegation child run completed.", contract)
        elif child.status in {"FAILED", "CANCELLED", "TIMEOUT"}:
            contract.status = "failed" if child.status == "FAILED" else child.status.lower()  # type: ignore[assignment]
            contract.completed_at = contract.completed_at or utc_now_iso()
            self._event(contract.parent_run_id, f"delegation_{contract.status}", contract.status, "Delegation child run reached terminal status.", contract)
        else:
            contract.status = "polling"
            self._event(contract.parent_run_id, "delegation_polling", "polling", "Delegation child run polled.", contract)
        saved = self.store.save_delegation(contract)
        return {
            "status": "ok",
            "delegation": saved.model_dump(),
            "child_session": child.model_dump() if child is not None else None,
            "source": "universal_task_session",
        }

    def cancel(self, delegation_id: str, *, reason: str = "cancelled_by_operator") -> DelegationContract | None:
        contract = self.store.get_delegation(delegation_id)
        if contract is None:
            return None
        contract.status = "cancelled"
        contract.completed_at = utc_now_iso()
        contract.updated_at = utc_now_iso()
        contract.review_status = "cancelled"
        self._event(contract.parent_run_id, "delegation_cancelled", "cancelled", reason, contract)
        return self.store.save_delegation(contract)

    def resume(self, delegation_id: str) -> dict[str, object] | None:
        contract = self.store.get_delegation(delegation_id)
        if contract is None:
            return None
        contract.status = "started"
        contract.updated_at = utc_now_iso()
        self._event(contract.parent_run_id, "delegation_started", "started", "Delegation resumed.", contract)
        self.store.save_delegation(contract)
        return self.poll(delegation_id)

    def timeout(self, delegation_id: str) -> DelegationContract | None:
        contract = self.store.get_delegation(delegation_id)
        if contract is None:
            return None
        contract.status = "timeout"
        contract.completed_at = utc_now_iso()
        contract.updated_at = utc_now_iso()
        contract.review_status = "timeout"
        self._event(contract.parent_run_id, "delegation_timeout", "timeout", "Delegation timed out.", contract)
        return self.store.save_delegation(contract)

    def _event(self, run_id: str, event_type: str, status: str, message: str, contract: DelegationContract) -> None:
        try:
            sequence = len(self.task_store.get_events(run_id)) + 1
            self.task_store.append_event(
                run_id,
                TaskRunEvent(
                    event_id=f"task_run_event_{uuid4().hex}",
                    run_id=run_id,
                    sequence=sequence,
                    type=event_type,
                    status=status,
                    message=message,
                    metadata={
                        "delegation_id": contract.delegation_id,
                        "child_run_id": contract.child_run_id,
                        "executor": contract.executor,
                        "polling_count": contract.polling_count,
                    },
                ),
            )
        except Exception:
            return
