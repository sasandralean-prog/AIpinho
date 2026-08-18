from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest, DelegationRequest, DelegationResult, DelegationStatusResponse
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_delegation_adapters import AgentAdapterRegistry
from aipinho.services.agents.agent_delegation_policy_service import AgentDelegationPolicyService
from aipinho.services.agents.agent_delegation_store import AgentDelegationStore
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.events.event_core import redact_payload


TERMINAL_STATUSES = {"completed", "completed_with_warnings", "blocked", "failed", "cancelled", "timed_out"}


class AgentDelegationService:
    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        store: AgentDelegationStore | None = None,
        policy: AgentDelegationPolicyService | None = None,
        adapters: AgentAdapterRegistry | None = None,
    ) -> None:
        self.kernel = kernel or AgentSessionKernelService()
        self.store = store or AgentDelegationStore()
        self.policy = policy or AgentDelegationPolicyService()
        self.adapters = adapters or AgentAdapterRegistry()

    def create_delegation(self, parent_agent_id: str, parent_run_id: str, request: DelegationCreateRequest) -> DelegationStatusResponse:
        parent_run = self.kernel.get_run(parent_run_id)
        if parent_run is None:
            raise FileNotFoundError(parent_run_id)
        if parent_run.agent_id != parent_agent_id:
            raise PermissionError("parent_run_agent_mismatch")

        execution_mode = request.execution_mode or str(parent_run.metadata_sanitized.get("execution_mode") or "governed_autorun")
        delegation = DelegationRequest(
            parent_agent_id=parent_agent_id,
            target_agent_id=request.target_agent_id,
            parent_session_id=parent_run.session_id,
            target_session_id=request.target_session_id,
            parent_run_id=parent_run_id,
            user_goal=str(redact_payload(request.user_goal)),
            requested_operation=request.requested_operation,
            operation_type=request.operation_type or request.requested_operation,
            workspace_id=request.workspace_id or parent_run.workspace_id,
            project_profile_id=request.project_profile_id,
            workspace_profile_id=request.workspace_profile_id,
            validation_profile_id=request.validation_profile_id,
            command_profile_ids=request.command_profile_ids,
            project_context_summary_sanitized=redact_payload(request.project_context_summary_sanitized),
            skill_id=request.skill_id,
            skill_version=request.skill_version,
            skill_inputs=redact_payload(request.skill_inputs),
            expected_skill_outputs=[str(redact_payload(item)) for item in request.expected_skill_outputs],
            capabilities_requested=request.capabilities_requested,
            constraints=redact_payload(request.constraints),
            expected_outputs=[str(redact_payload(item)) for item in request.expected_outputs],
            memory_refs=[str(redact_payload(item)) for item in request.memory_refs],
            memory_context_sanitized=redact_payload(request.memory_context_sanitized),
            risk_level=request.risk_level,
            execution_mode=execution_mode,
            autoapproval_policy=redact_payload(request.autoapproval_policy),
            timeout_seconds=self.policy.timeout_seconds(request.timeout_seconds),
            max_child_steps=request.max_child_steps,
            status="created",
            evidence_refs=[f"run:{parent_run_id}"],
            metadata_sanitized=redact_payload(request.metadata_sanitized),
        )
        delegation = self.store.save_request(delegation)
        self._event(parent_run_id, "delegation_created", f"{parent_agent_id} solicitou delegacao para {delegation.target_agent_id}.", delegation, {"target_agent_id": delegation.target_agent_id})
        if delegation.memory_refs or delegation.memory_context_sanitized:
            self._event(parent_run_id, "memory_context_attached_to_delegation", "Contexto de memoria sanitizado anexado a delegacao.", delegation, {"memory_refs": delegation.memory_refs, "has_memory_context": bool(delegation.memory_context_sanitized)}, severity="info")
        self._event(parent_run_id, "delegation_policy_check_started", "Verificando policy de delegacao.", delegation, {})

        parent_profile = self.kernel.get_profile(parent_agent_id)
        target_profile = self.kernel.get_profile(delegation.target_agent_id)
        lineage = self._lineage(parent_run)
        cycle = delegation.target_agent_id in {run.agent_id for run in lineage}
        child_count = len(self.store.list_requests(parent_run_id=parent_run_id))
        decision = self.policy.evaluate(
            delegation,
            parent_profile=parent_profile,
            target_profile=target_profile,
            cycle_detected=cycle,
            depth=len(lineage),
            child_count=max(0, child_count - 1),
        )
        self.store.save_policy_decision(decision)
        self._event(parent_run_id, "delegation_policy_check_completed", decision.human_reason, delegation, {"decision": decision.decision, "reason_code": decision.reason_code})

        if decision.decision == "deny":
            delegation = self.store.save_request(delegation.model_copy(update={"status": "blocked", "evidence_refs": [*delegation.evidence_refs, decision.policy_decision_id]}))
            result = self._blocked_result(delegation, decision.reason_code, decision.human_reason, metadata_sanitized=decision.metadata_sanitized)
            self.store.save_result(result)
            self._event(parent_run_id, "delegation_blocked", decision.human_reason, delegation, {"reason_code": decision.reason_code, "metadata": decision.metadata_sanitized}, severity="warning")
            return DelegationStatusResponse(status="blocked", delegation=delegation, policy_decision=decision, result=result)

        if decision.decision == "require_approval":
            delegation = self.store.save_request(delegation.model_copy(update={"status": "approval_required", "evidence_refs": [*delegation.evidence_refs, decision.policy_decision_id]}))
            result = DelegationResult(
                delegation_id=delegation.delegation_id,
                parent_run_id=delegation.parent_run_id,
                parent_agent_id=delegation.parent_agent_id,
                target_agent_id=delegation.target_agent_id,
                status="approval_required",
                summary=decision.human_reason,
                reason_code=decision.reason_code,
                evidence_refs=[f"delegation:{delegation.delegation_id}", decision.policy_decision_id],
                next_steps=["Aguardar aprovacao humana antes de criar child run."],
            )
            self.store.save_result(result)
            self.kernel.update_run(parent_run_id, AgentRunUpdateRequest(status="pending_approval", metadata_sanitized={"delegation_id": delegation.delegation_id, "reason_code": decision.reason_code}))
            self._event(parent_run_id, "delegation_approval_required", decision.human_reason, delegation, {"reason_code": decision.reason_code}, severity="warning")
            return DelegationStatusResponse(status="approval_required", delegation=delegation, policy_decision=decision, result=result)

        target_session = self._ensure_target_session(delegation)
        child_run = self.kernel.create_run(
            delegation.target_agent_id,
            target_session.session_id,
            AgentRunCreateRequest(
                operation_type=delegation.operation_type,
                parent_run_id=parent_run_id,
                delegation_id=delegation.delegation_id,
                status="running",
                workspace_id=delegation.workspace_id,
                capabilities_requested=delegation.capabilities_requested,
                metadata_sanitized={
                    "delegation_id": delegation.delegation_id,
                    "parent_agent_id": delegation.parent_agent_id,
                    "parent_run_id": parent_run_id,
                    "project_profile_id": delegation.project_profile_id,
                    "workspace_profile_id": delegation.workspace_profile_id,
                    "validation_profile_id": delegation.validation_profile_id,
                    "command_profile_ids": delegation.command_profile_ids,
                    "project_context_summary_sanitized": delegation.project_context_summary_sanitized,
                    "skill_id": delegation.skill_id,
                    "skill_version": delegation.skill_version,
                    "expected_skill_outputs": delegation.expected_skill_outputs,
                    "execution_mode": delegation.execution_mode,
                    "requested_operation": delegation.requested_operation,
                    "memory_refs": delegation.memory_refs,
                    "has_memory_context": bool(delegation.memory_context_sanitized),
                },
            ),
        )
        delegation = self.store.save_request(
            delegation.model_copy(
                update={
                    "status": "running",
                    "target_session_id": target_session.session_id,
                    "child_run_id": child_run.run_id,
                    "evidence_refs": [*delegation.evidence_refs, decision.policy_decision_id, f"run:{child_run.run_id}"],
                }
            )
        )
        if decision.decision == "auto_approve":
            self._event(parent_run_id, "delegation_auto_approved", decision.human_reason, delegation, {"auto_approval_id": decision.auto_approval_id})
        self._event(parent_run_id, "delegation_accepted", f"Delegacao aceita por {delegation.target_agent_id}.", delegation, {"child_run_id": child_run.run_id})
        self._event(parent_run_id, "delegation_child_session_created", "Sessao filha de delegacao registrada.", delegation, {"target_session_id": target_session.session_id})
        self._event(parent_run_id, "delegation_child_run_created", "Child run de delegacao criado.", delegation, {"child_run_id": child_run.run_id})
        self._event(parent_run_id, "delegation_child_run_started", f"{delegation.target_agent_id} iniciou child run.", delegation, {"child_run_id": child_run.run_id})
        self._event(child_run.run_id, "delegation_child_run_started", f"{delegation.target_agent_id} recebeu delegacao de {delegation.parent_agent_id}.", delegation, {"parent_run_id": parent_run_id})
        if delegation.memory_refs or delegation.memory_context_sanitized:
            self._event(child_run.run_id, "memory_context_attached_to_delegation", "Contexto de memoria sanitizado recebido pela delegacao.", delegation, {"memory_refs": delegation.memory_refs, "has_memory_context": bool(delegation.memory_context_sanitized)}, severity="info")
        self.kernel.update_run(parent_run_id, AgentRunUpdateRequest(status="delegation_running", metadata_sanitized={"delegation_id": delegation.delegation_id, "child_run_id": child_run.run_id}))

        adapter = self.adapters.get(delegation.target_agent_id)
        result = adapter.summarize_result(delegation, child_run)
        self.store.save_result(result)
        return DelegationStatusResponse(status="running", delegation=delegation, policy_decision=decision, result=result)

    def get_delegation(self, delegation_id: str) -> DelegationStatusResponse:
        delegation = self.store.get_request(delegation_id)
        if delegation is None:
            raise FileNotFoundError(delegation_id)
        return DelegationStatusResponse(
            status=delegation.status,
            delegation=delegation,
            policy_decision=self.store.get_policy_decision(delegation_id),
            result=self.store.get_result(delegation_id),
        )

    def result(self, delegation_id: str) -> DelegationResult:
        result = self.store.get_result(delegation_id)
        if result is None:
            raise FileNotFoundError(delegation_id)
        return result

    def cancel(self, delegation_id: str) -> DelegationStatusResponse:
        delegation = self.store.get_request(delegation_id)
        if delegation is None:
            raise FileNotFoundError(delegation_id)
        if delegation.status in TERMINAL_STATUSES:
            return self.get_delegation(delegation_id)
        delegation = self.store.save_request(delegation.model_copy(update={"status": "cancelled"}))
        if delegation.child_run_id:
            self.kernel.update_run(delegation.child_run_id, AgentRunUpdateRequest(status="cancelled", metadata_sanitized={"delegation_id": delegation.delegation_id}))
        self.kernel.update_run(delegation.parent_run_id, AgentRunUpdateRequest(status="cancelled", metadata_sanitized={"delegation_id": delegation.delegation_id}))
        self._event(delegation.parent_run_id, "delegation_cancelled", "Delegacao cancelada.", delegation, {}, severity="warning")
        if delegation.child_run_id:
            self._event(delegation.child_run_id, "delegation_cancelled", "Child run cancelado pela delegacao.", delegation, {}, severity="warning")
        result = DelegationResult(
            delegation_id=delegation.delegation_id,
            parent_run_id=delegation.parent_run_id,
            child_run_id=delegation.child_run_id,
            parent_agent_id=delegation.parent_agent_id,
            target_agent_id=delegation.target_agent_id,
            status="cancelled",
            summary="Delegacao cancelada de forma controlada.",
            completed_at=utc_now_iso(),
            evidence_refs=[f"delegation:{delegation.delegation_id}"],
        )
        self.store.save_result(result)
        return self.get_delegation(delegation_id)

    def check_timeout(self, delegation_id: str) -> DelegationStatusResponse:
        delegation = self.store.get_request(delegation_id)
        if delegation is None:
            raise FileNotFoundError(delegation_id)
        if delegation.status in TERMINAL_STATUSES:
            return self.get_delegation(delegation_id)
        created = datetime.fromisoformat(delegation.created_at.replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - created).total_seconds() < delegation.timeout_seconds:
            return self.get_delegation(delegation_id)
        delegation = self.store.save_request(delegation.model_copy(update={"status": "timed_out"}))
        if delegation.child_run_id:
            self.kernel.update_run(delegation.child_run_id, AgentRunUpdateRequest(status="cancelled", error_code="delegation_timeout", metadata_sanitized={"delegation_id": delegation.delegation_id}))
        self.kernel.update_run(delegation.parent_run_id, AgentRunUpdateRequest(status="failed", error_code="delegation_timeout", metadata_sanitized={"delegation_id": delegation.delegation_id}))
        self._event(delegation.parent_run_id, "delegation_timed_out", "Delegacao expirou por timeout.", delegation, {"reason_code": "delegation_timeout"}, severity="error")
        result = self._blocked_result(delegation, "delegation_timeout", "Delegacao expirou por timeout.", status="timed_out")
        self.store.save_result(result)
        return self.get_delegation(delegation_id)

    def children(self, run_id: str) -> list[DelegationRequest]:
        return self.store.list_requests(parent_run_id=run_id)

    def parent(self, run_id: str) -> DelegationRequest | None:
        rows = self.store.list_requests(child_run_id=run_id)
        return rows[0] if rows else None

    def _ensure_target_session(self, delegation: DelegationRequest):
        if delegation.target_session_id:
            session = self.kernel.get_session(delegation.target_agent_id, delegation.target_session_id, include_compat=False)
            if session is not None:
                return session
        return self.kernel.create_session(
            delegation.target_agent_id,
            AgentSessionCreateRequest(
                title=f"Delegated from {delegation.parent_agent_id}",
                active_workspace_id=delegation.workspace_id,
                metadata_sanitized={
                    "delegation_id": delegation.delegation_id,
                    "parent_agent_id": delegation.parent_agent_id,
                    "project_profile_id": delegation.project_profile_id,
                    "project_context_summary_sanitized": delegation.project_context_summary_sanitized,
                    "skill_id": delegation.skill_id,
                    "skill_version": delegation.skill_version,
                },
            ),
        )

    def _lineage(self, run) -> list:
        rows = []
        current = run
        while current is not None:
            rows.append(current)
            current = self.kernel.get_run(current.parent_run_id) if current.parent_run_id else None
        return rows

    def _event(self, run_id: str, event_type: str, message: str, delegation: DelegationRequest, payload: dict, *, severity: str = "info") -> None:
        run = self.kernel.get_run(run_id)
        if run is None:
            return
        data = {
            "delegation_id": delegation.delegation_id,
            "parent_agent_id": delegation.parent_agent_id,
            "target_agent_id": delegation.target_agent_id,
            "project_profile_id": delegation.project_profile_id,
            "workspace_profile_id": delegation.workspace_profile_id,
            "validation_profile_id": delegation.validation_profile_id,
            "skill_id": delegation.skill_id,
            "skill_version": delegation.skill_version,
            **payload,
        }
        self.kernel.add_event(
            run_id,
            AgentEventCreateRequest(
                event_type=event_type,
                severity=severity,
                human_message=message,
                technical_summary_sanitized=event_type,
                payload_sanitized=data,
                delegation_id=delegation.delegation_id,
                evidence_refs=[f"delegation:{delegation.delegation_id}", f"run:{run_id}"],
            ),
        )

    def _blocked_result(
        self,
        delegation: DelegationRequest,
        reason_code: str,
        summary: str,
        *,
        status: str = "blocked",
        metadata_sanitized: dict | None = None,
    ) -> DelegationResult:
        return DelegationResult(
            delegation_id=delegation.delegation_id,
            parent_run_id=delegation.parent_run_id,
            child_run_id=delegation.child_run_id,
            parent_agent_id=delegation.parent_agent_id,
            target_agent_id=delegation.target_agent_id,
            status=status,
            summary=str(redact_payload(summary)),
            reason_code=reason_code,
            errors=[reason_code],
            next_steps=["Retornar ao agente pai com resumo e pedir decisao do usuario."],
            completed_at=utc_now_iso(),
            evidence_refs=[f"delegation:{delegation.delegation_id}"],
            metadata_sanitized=redact_payload(metadata_sanitized or {}),
        )
