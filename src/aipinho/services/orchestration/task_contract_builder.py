from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from aipinho.schemas.chat.session_state import SessionState
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.orchestration.task_draft_policy_service import TaskDraftPolicyService
from aipinho.services.runtime.runtime_profile_service import RuntimeProfileService


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


class TaskContractBuilder:
    def __init__(self, policy: TaskDraftPolicyService | None = None) -> None:
        self.policy = policy or TaskDraftPolicyService().load()
        self.profiles = RuntimeProfileService().load()

    def build_draft(self, intent_map: Any, policy_decision: Any, session_state: SessionState | None = None) -> TaskContractDraft | None:
        intent_type = getattr(intent_map, "intent_type", "unknown")
        if not self.policy.should_create_for_intent(intent_type):
            return None
        now = datetime.now(timezone.utc)
        workspace = self._workspace(intent_map, session_state)
        status = self._status(intent_map, policy_decision, workspace)
        questions = self._clarifying_questions(intent_map, workspace, status)
        operation_type = str(getattr(intent_map, "operation_type", "unknown"))
        contract_type = str(getattr(policy_decision, "contract_type", getattr(intent_map, "task_type", "unknown")))
        profile = self.profiles.resolve(operation_type=operation_type, contract_type=contract_type) or {}
        safe_to_execute = self._safe_to_execute(policy_decision, status)
        if contract_type.startswith("readonly") or not list(getattr(intent_map, "requested_actions", [])):
            safe_to_execute = False
        return TaskContractDraft(
            draft_id=f"draft_{uuid4().hex}",
            session_id=session_state.session_id if session_state else None,
            status=status,
            intent_map=self._intent_summary(intent_map),
            policy_decision=self._policy_summary(policy_decision),
            contract_type=contract_type,
            operation_type=operation_type,
            intent_type=intent_type,
            runtime_profile=str(profile.get("id") or "") or None,
            capabilities_required=list(profile.get("required_capabilities", []) or []),
            source_scope=self._source_scope(workspace),
            requires_workspace=bool(getattr(intent_map, "requires_workspace", False)),
            workspace=workspace,
            requested_actions=list(getattr(intent_map, "requested_actions", [])),
            allowed_actions=list(getattr(policy_decision, "allowed_actions", [])),
            denied_actions=list(getattr(policy_decision, "denied_actions", [])),
            approval_required_for=list(getattr(policy_decision, "approval_required_for", [])),
            safe_to_execute=safe_to_execute,
            safe_to_preview=bool(getattr(policy_decision, "safe_to_preview", False)) and status != "blocked",
            clarifying_questions=questions,
            warnings=list(dict.fromkeys([*getattr(intent_map, "warnings", []), *getattr(policy_decision, "warnings", [])])),
            trace=[self._trace_summary(item) for item in getattr(policy_decision, "trace", [])],
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=self.policy.ttl_minutes())).isoformat(),
        )

    def _safe_to_execute(self, policy_decision: Any, status: str) -> bool:
        if status in {"blocked", "needs_clarification", "approval_required"}:
            return False
        if getattr(policy_decision, "status", "") not in {"allowed", "approved"}:
            return False
        return bool(getattr(policy_decision, "safe_to_execute", False))

    def _source_scope(self, workspace: TaskDraftWorkspace) -> str | None:
        if workspace.status == "not_required":
            return "none"
        if workspace.status == "protected":
            return "protected"
        return "workspace"

    def _workspace(self, intent_map: Any, session_state: SessionState | None) -> TaskDraftWorkspace:
        workspace = getattr(intent_map, "workspace", None)
        requires_workspace = bool(getattr(intent_map, "requires_workspace", False))
        if workspace is not None and getattr(workspace, "protected", False):
            return TaskDraftWorkspace(path=getattr(workspace, "path", None), status="protected")
        if workspace is not None and getattr(workspace, "declared", False):
            return TaskDraftWorkspace(path=getattr(workspace, "path", None), status="confirmed")
        if requires_workspace and session_state and session_state.active_workspace_candidate:
            return TaskDraftWorkspace(path=session_state.active_workspace_candidate, status="candidate")
        if requires_workspace:
            return TaskDraftWorkspace(path=None, status="missing")
        return TaskDraftWorkspace(path=None, status="not_required")

    def _status(self, intent_map: Any, policy_decision: Any, workspace: TaskDraftWorkspace):
        if workspace.status == "protected" or getattr(policy_decision, "status", "") == "denied":
            return "blocked"
        ambiguity = getattr(intent_map, "ambiguity", None)
        if ambiguity is not None and getattr(ambiguity, "requires_clarification", False):
            return "needs_clarification"
        if workspace.status in {"missing", "candidate"} and self.policy.require_workspace_confirmation():
            return "needs_clarification"
        if getattr(policy_decision, "approval_required_for", []):
            return "approval_required"
        return "draft"

    def _clarifying_questions(self, intent_map: Any, workspace: TaskDraftWorkspace, status: str) -> list[str]:
        questions: list[str] = []
        if workspace.status == "missing":
            questions.append("Qual workspace ou projeto devo usar?")
        if workspace.status == "candidate":
            questions.append("Confirma que devo usar o workspace candidato antes de preparar a task?")
        if status == "needs_clarification" and not questions:
            questions.append("Pode detalhar o objetivo, escopo e resultado esperado?")
        return questions

    def _intent_summary(self, intent_map: Any) -> dict[str, Any]:
        workspace = getattr(intent_map, "workspace", None)
        return {
            "intent_id": getattr(intent_map, "intent_id", None),
            "intent_type": getattr(intent_map, "intent_type", "unknown"),
            "task_type": getattr(intent_map, "task_type", "none"),
            "operation_type": getattr(intent_map, "operation_type", "unknown"),
            "requires_task": getattr(intent_map, "requires_task", False),
            "requires_workspace": getattr(intent_map, "requires_workspace", False),
            "risk": getattr(getattr(intent_map, "risk", None), "level", "unknown"),
            "workspace": {
                "path": getattr(workspace, "path", None),
                "declared": getattr(workspace, "declared", False),
                "protected": getattr(workspace, "protected", False),
            },
            "workspace_references": [
                _dump_model(item)
                for item in getattr(intent_map, "workspace_references", [])
            ],
            "requested_deliverables": list(
                getattr(intent_map, "requested_deliverables", [])
            ),
        }

    def _policy_summary(self, policy_decision: Any) -> dict[str, Any]:
        return {
            "status": getattr(policy_decision, "status", "unknown"),
            "contract_type": getattr(policy_decision, "contract_type", "unknown"),
            "allowed_actions": list(getattr(policy_decision, "allowed_actions", [])),
            "denied_actions": list(getattr(policy_decision, "denied_actions", [])),
            "approval_required_for": list(getattr(policy_decision, "approval_required_for", [])),
            "safe_to_preview": bool(getattr(policy_decision, "safe_to_preview", False)),
            "safe_to_execute": bool(getattr(policy_decision, "safe_to_execute", False)),
        }

    def _trace_summary(self, trace_item: Any) -> dict[str, Any]:
        data = _dump_model(trace_item)
        return {
            "stage": data.get("stage", "unknown"),
            "decision": data.get("decision", "unknown"),
            "reason": data.get("reason", ""),
            "source": data.get("source"),
        }
