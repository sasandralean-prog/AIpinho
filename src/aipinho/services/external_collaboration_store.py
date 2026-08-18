from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, TypeVar

from aipinho.core.paths import PATHS
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.external_collaboration import (
    ContinuousCollaborationSession,
    ExternalConversationRecord,
    ExternalReviewContract,
    ExternalTaskContract,
    SuccessContract,
    SuccessEvaluation,
)
from aipinho.schemas.runtime.delegation_contract import DelegationContract

T = TypeVar("T", bound=AIpinhoModel)

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+")
_SENSITIVE_KEYS = {"api_key", "token", "password", "secret", "raw_prompt", "raw_content"}


class ExternalCollaborationStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "external_collaboration"

    def save_success_contract(self, contract: SuccessContract) -> SuccessContract:
        return self._save("success_contracts", contract.success_contract_id, contract)

    def get_success_contract(self, contract_id: str) -> SuccessContract | None:
        return self._get("success_contracts", contract_id, SuccessContract)

    def save_task(self, task: ExternalTaskContract) -> ExternalTaskContract:
        return self._save("tasks", task.external_task_id, task)

    def get_task(self, task_id: str) -> ExternalTaskContract | None:
        return self._get("tasks", task_id, ExternalTaskContract)

    def save_review(self, review: ExternalReviewContract) -> ExternalReviewContract:
        return self._save("reviews", review.review_id, review)

    def get_review(self, review_id: str) -> ExternalReviewContract | None:
        return self._get("reviews", review_id, ExternalReviewContract)

    def list_reviews(self, *, task_run_id: str | None = None, external_task_id: str | None = None, limit: int = 100) -> list[ExternalReviewContract]:
        rows = self._list("reviews", ExternalReviewContract)
        if task_run_id:
            rows = [row for row in rows if row.task_run_id == task_run_id]
        if external_task_id:
            rows = [row for row in rows if row.external_task_id == external_task_id]
        return rows[: max(1, min(limit, 1000))]

    def save_evaluation(self, evaluation: SuccessEvaluation) -> SuccessEvaluation:
        return self._save("success_evaluations", evaluation.evaluation_id, evaluation)

    def get_evaluation(self, evaluation_id: str) -> SuccessEvaluation | None:
        return self._get("success_evaluations", evaluation_id, SuccessEvaluation)

    def list_evaluations(self, *, session_id: str | None = None, task_run_id: str | None = None, limit: int = 100) -> list[SuccessEvaluation]:
        rows = self._list("success_evaluations", SuccessEvaluation)
        if session_id:
            rows = [row for row in rows if row.session_id == session_id]
        if task_run_id:
            rows = [row for row in rows if row.task_run_id == task_run_id]
        return rows[: max(1, min(limit, 1000))]

    def save_conversation(self, conversation: ExternalConversationRecord) -> ExternalConversationRecord:
        return self._save("conversations", conversation.conversation_id, conversation)

    def get_conversation(self, conversation_id: str) -> ExternalConversationRecord | None:
        return self._get("conversations", conversation_id, ExternalConversationRecord)

    def save_collaboration_session(self, session: ContinuousCollaborationSession) -> ContinuousCollaborationSession:
        return self._save("continuous_sessions", session.session_id, session)

    def get_collaboration_session(self, session_id: str) -> ContinuousCollaborationSession | None:
        return self._get("continuous_sessions", session_id, ContinuousCollaborationSession)

    def list_collaboration_sessions(self, *, task_run_id: str | None = None, status: str | None = None, limit: int = 100) -> list[ContinuousCollaborationSession]:
        rows = self._list("continuous_sessions", ContinuousCollaborationSession)
        if task_run_id:
            rows = [row for row in rows if row.task_run_id == task_run_id]
        if status:
            rows = [row for row in rows if row.status == status]
        return rows[: max(1, min(limit, 1000))]

    def save_delegation(self, delegation: DelegationContract) -> DelegationContract:
        return self._save("delegations", delegation.delegation_id, delegation)

    def get_delegation(self, delegation_id: str) -> DelegationContract | None:
        return self._get("delegations", delegation_id, DelegationContract)

    def list_delegations(
        self,
        *,
        parent_run_id: str | None = None,
        child_run_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[DelegationContract]:
        rows = self._list("delegations", DelegationContract)
        if parent_run_id:
            rows = [row for row in rows if row.parent_run_id == parent_run_id]
        if child_run_id:
            rows = [row for row in rows if row.child_run_id == child_run_id]
        if status:
            rows = [row for row in rows if row.status == status]
        return rows[: max(1, min(limit, 1000))]

    def _save(self, bucket: str, item_id: str, model: T) -> T:
        path = self._path(bucket, item_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._sanitize(model.model_dump()), ensure_ascii=False, indent=2), encoding="utf-8")
        return model

    def _get(self, bucket: str, item_id: str, model_type: type[T]) -> T | None:
        path = self._path(bucket, item_id)
        if not path.exists():
            return None
        return model_type.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))

    def _list(self, bucket: str, model_type: type[T]) -> list[T]:
        base = self.root / bucket
        if not base.exists():
            return []
        rows: list[T] = []
        for path in base.glob("*.json"):
            try:
                rows.append(model_type.model_validate(json.loads(path.read_text(encoding="utf-8-sig"))))
            except Exception:
                continue
        return sorted(rows, key=lambda item: str(getattr(item, "updated_at", getattr(item, "received_at", ""))), reverse=True)

    def _path(self, bucket: str, item_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", item_id):
            raise ValueError("invalid_external_collaboration_id")
        return self.root / bucket / f"{item_id}.json"

    def _sanitize(self, value: Any, *, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS:
            return "[omitted_by_external_collaboration_store]"
        if isinstance(value, dict):
            return {str(k): self._sanitize(v, key=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if isinstance(value, str):
            return _SECRET.sub("[REDACTED]", value)[:30000]
        return value
