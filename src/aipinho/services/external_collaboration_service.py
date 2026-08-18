from __future__ import annotations

from typing import Any

from aipinho.schemas.external_collaboration import (
    ContinuousCollaborationPollResponse,
    ContinuousCollaborationSession,
    ContinuousCollaborationStartRequest,
    ExternalAdapterOutput,
    ExternalAdapterEvaluationOutput,
    ExternalAdapterEvaluationRequest,
    ExternalAdapterReviewRequest,
    ExternalConversationCreateRequest,
    ExternalConversationRecord,
    ExternalReviewContract,
    ExternalReviewCreateRequest,
    ExternalTaskContract,
    ExternalTaskCreateRequest,
    SuccessContract,
    SuccessContractCreateRequest,
    SuccessContractRuntime,
    SuccessEvaluation,
    SuccessEvaluationCreateRequest,
)
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.delegation_contract import (
    DelegationContract,
    DelegationCreateRequest,
    DelegationDecisionResult,
)
from aipinho.services.external_adapter_registry import ExternalAdapterRegistry
from aipinho.services.external_collaboration_store import ExternalCollaborationStore
from aipinho.services.runtime.delegation_decision_engine import DelegationDecisionEngine
from aipinho.services.runtime.delegation_polling_service import DelegationPollingService
from aipinho.services.runtime.delegation_truth_validator import DelegationTruthValidator
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


class ExternalCollaborationService:
    """Provider-neutral public collaboration boundary.

    External models can submit contracts and reviews here, but execution,
    approval, validation and final authority stay inside AIpinho.
    """

    def __init__(
        self,
        *,
        store: ExternalCollaborationStore | None = None,
        runtime: TaskRuntimeService | None = None,
        universal_sessions: UniversalTaskSessionService | None = None,
        adapters: ExternalAdapterRegistry | None = None,
        delegation_engine: DelegationDecisionEngine | None = None,
    ) -> None:
        self.store = store or ExternalCollaborationStore()
        self.runtime = runtime or TaskRuntimeService()
        self.universal_sessions = universal_sessions or UniversalTaskSessionService(
            store=self.runtime.store,
            approvals=self.runtime.approvals,
        )
        self.adapters = adapters or ExternalAdapterRegistry()
        self.delegation_engine = delegation_engine or DelegationDecisionEngine()
        self.delegation_polling = DelegationPollingService(
            store=self.store,
            task_store=self.runtime.store,
            universal_sessions=self.universal_sessions,
        )

    def create_success_contract(self, request: SuccessContractCreateRequest) -> SuccessContract:
        contract = SuccessContract(
            objective=request.objective,
            acceptance_criteria=list(request.acceptance_criteria),
            forbidden=list(request.forbidden),
            required_evidence=list(request.required_evidence),
            completion_definition=request.completion_definition,
            priority=request.priority,
            created_by=request.created_by,
            metadata=dict(request.metadata),
        )
        return self.store.save_success_contract(contract)

    def get_success_contract(self, contract_id: str) -> SuccessContract | None:
        return self.store.get_success_contract(contract_id)

    def create_conversation(self, request: ExternalConversationCreateRequest) -> ExternalConversationRecord:
        conversation = ExternalConversationRecord(
            provider=request.provider,
            session_id=request.session_id,
            related_task_id=request.related_task_id,
            related_review_id=request.related_review_id,
            title=request.title,
            metadata=dict(request.metadata),
        )
        return self.store.save_conversation(conversation)

    def get_conversation(self, conversation_id: str) -> ExternalConversationRecord | None:
        return self.store.get_conversation(conversation_id)

    def submit_task(self, request: ExternalTaskCreateRequest) -> dict[str, Any]:
        task = ExternalTaskContract(
            provider=request.provider,
            objective=request.objective,
            context=dict(request.context),
            expected_output=request.expected_output,
            constraints=list(request.constraints),
            deadline=request.deadline,
            success_contract_id=request.success_contract_id,
            conversation_id=request.conversation_id,
            status="admitted",
            metadata={
                **request.metadata,
                "contract_type": request.contract_type,
                "operation_type": request.operation_type,
                "runtime_profile": request.runtime_profile,
                "authority_boundary": "external_models_submit_contracts_only",
            },
        )
        if request.create_task_run:
            run = self.runtime.create_run(
                TaskRunRequest(
                    source_type="direct",
                    session_id=request.session_id or request.conversation_id,
                    workspace=request.workspace,
                    contract_type=request.contract_type,
                    operation_type=request.operation_type,
                    runtime_profile=request.runtime_profile,
                    requested_actions=[],
                    policy_decision=self._external_policy_snapshot(request),
                    intent_map={
                        "source": "external_agent_interface",
                        "provider": request.provider,
                        "external_task_id": task.external_task_id,
                        "success_contract_id": request.success_contract_id,
                        "objective": request.objective,
                        "authority": "aipinho",
                        "external_authority": "none",
                    },
                    start_immediately=False,
                )
            )
            task.related_task_run_id = run.run_id
            task.status = "task_run_created"
        saved = self.store.save_task(task)
        return {
            "status": "ok",
            "external_task": saved.model_dump(),
            "task_run_id": saved.related_task_run_id,
            "universal_task_session": self._session_payload(saved.related_task_run_id),
            "authority": "aipinho",
            "external_may_execute": False,
        }

    def get_task(self, external_task_id: str) -> ExternalTaskContract | None:
        return self.store.get_task(external_task_id)

    def task_payload(self, external_task_id: str) -> dict[str, Any] | None:
        task = self.get_task(external_task_id)
        if task is None:
            return None
        return {
            "external_task": task.model_dump(),
            "universal_task_session": self._session_payload(task.related_task_run_id),
            "authority": "aipinho",
        }

    def task_progress(self, external_task_id: str) -> dict[str, Any] | None:
        task = self.get_task(external_task_id)
        if task is None:
            return None
        summary = self.universal_sessions.summary(task.related_task_run_id) if task.related_task_run_id else None
        return {
            "external_task_id": task.external_task_id,
            "task_run_id": task.related_task_run_id,
            "progress": (summary or {}).get("progress"),
            "status": (summary or {}).get("status", task.status),
            "phase": (summary or {}).get("phase", "external_contract_received"),
            "last_event": (summary or {}).get("last_event"),
            "source": "universal_task_session",
        }

    def task_summary(self, external_task_id: str) -> dict[str, Any] | None:
        task = self.get_task(external_task_id)
        if task is None:
            return None
        if task.related_task_run_id:
            return self.universal_sessions.summary(task.related_task_run_id)
        return {"external_task_id": task.external_task_id, "status": task.status, "summary": task.objective}

    def task_artifacts(self, external_task_id: str) -> dict[str, Any] | None:
        task = self.get_task(external_task_id)
        if task is None:
            return None
        if task.related_task_run_id:
            return self.universal_sessions.artifacts_for_run(task.related_task_run_id)
        return {"external_task_id": task.external_task_id, "artifacts": [], "count": 0, "source": "universal_task_session"}

    def decide_delegation(self, request: DelegationCreateRequest) -> DelegationDecisionResult:
        return self.delegation_engine.decide(
            prompt=request.objective,
            provider=request.provider,
            context={**request.context, "workspace": request.workspace},
            metadata=request.metadata,
        )

    def create_delegation(self, request: DelegationCreateRequest) -> dict[str, Any]:
        decision = self.decide_delegation(request)
        if decision.decision == "DIRECT_RESPONSE":
            return {
                "status": "direct_response",
                "mode": "direct_response",
                "delegation_id": None,
                "child_run_id": None,
                "decision": decision.model_dump(),
                "message": "Resposta direta do Provider; sem delegacao.",
                "external_may_execute": False,
                "authority": "aipinho",
            }
        if decision.decision in {"BLOCK", "REQUIRES_APPROVAL"}:
            return {
                "status": "blocked" if decision.blocked else "requires_approval",
                "mode": decision.decision.lower(),
                "delegation_id": None,
                "child_run_id": None,
                "decision": decision.model_dump(),
                "external_may_execute": False,
                "authority": "aipinho",
            }
        parent = self._parent_run_for_delegation(request)
        child = self.runtime.create_run(
            TaskRunRequest(
                source_type="direct",
                session_id=request.session_id,
                workspace=request.workspace,
                contract_type=request.contract_type,
                operation_type=request.operation_type,
                runtime_profile=request.runtime_profile,
                requested_actions=[],
                policy_decision=self._delegation_policy_snapshot(request, decision),
                intent_map={
                    "source": "external_delegation_child",
                    "provider": request.provider,
                    "parent_run_id": parent.run_id,
                    "objective": request.objective,
                    "authority": "aipinho",
                    "external_authority": "none",
                },
                start_immediately=False,
            )
        )
        contract = DelegationContract(
            parent_run_id=parent.run_id,
            child_run_id=child.run_id,
            executor=decision.executor,
            status="started",
            reason=request.reason or decision.reason,
            routing_policy=decision.routing_policy,
            workspace=request.workspace,
            provider=request.provider,
            speaker_truth_hash=DelegationTruthValidator.truth_hash(request.objective, None),
            evidence_refs=[f"task_run:{parent.run_id}", f"task_run:{child.run_id}"],
            metadata={
                **request.metadata,
                "decision": decision.model_dump(),
                "context": request.context,
                "authority": "aipinho",
            },
        )
        parent.intent_map["delegation_id"] = contract.delegation_id
        parent.intent_map["child_run_id"] = child.run_id
        child.intent_map["delegation_id"] = contract.delegation_id
        child.intent_map["parent_run_id"] = parent.run_id
        self.runtime.store.update_run(parent)
        self.runtime.store.update_run(child)
        saved = self.store.save_delegation(contract)
        self._delegation_event(parent.run_id, "delegation_created", "created", "Delegation contract created.", saved)
        self._delegation_event(parent.run_id, "delegation_started", "started", "Delegation runtime started.", saved)
        self._delegation_event(parent.run_id, "delegation_forwarded", "forwarded", "Delegation forwarded to child TaskRun.", saved)
        return {
            "status": "ok",
            "mode": "delegated",
            "decision": decision.model_dump(),
            "delegation": saved.model_dump(),
            "delegation_id": saved.delegation_id,
            "parent_run_id": saved.parent_run_id,
            "child_run_id": saved.child_run_id,
            "parent_session": self._session_payload(parent.run_id),
            "child_session": self._session_payload(child.run_id),
            "external_may_execute": False,
            "authority": "aipinho",
        }

    def get_delegation(self, delegation_id: str) -> DelegationContract | None:
        return self.store.get_delegation(delegation_id)

    def list_delegations(self, *, parent_run_id: str | None = None, child_run_id: str | None = None, status: str | None = None, limit: int = 100) -> list[DelegationContract]:
        return self.store.list_delegations(parent_run_id=parent_run_id, child_run_id=child_run_id, status=status, limit=limit)

    def poll_delegation(self, delegation_id: str) -> dict[str, object] | None:
        return self.delegation_polling.poll(delegation_id)

    def receive_review(self, request: ExternalReviewCreateRequest) -> ExternalReviewContract:
        delegation_id = str(request.metadata.get("delegation_id") or "") or None
        delegation_truth = DelegationTruthValidator().validate(request.raw_summary, delegation_id=delegation_id)
        missing_evidence = list(dict.fromkeys([*request.missing_evidence, *delegation_truth.violations]))
        review = ExternalReviewContract(
            provider=request.provider,
            task_run_id=request.task_run_id,
            external_task_id=request.external_task_id,
            conversation_id=request.conversation_id,
            status=request.status,
            confidence=request.confidence,
            findings=list(request.findings),
            recommendations=list(request.recommendations),
            missing_evidence=missing_evidence,
            next_action="review_loop" if delegation_truth.violations else request.next_action,
            raw_summary=request.raw_summary,
            metadata={
                **request.metadata,
                "aipinho_authority": True,
                "external_authority": "none",
                "automatic_execution": False,
                "speaker_truth_mode": "auditor",
                "delegation_truth": delegation_truth.model_dump(),
            },
        )
        return self.store.save_review(review)

    def get_review(self, review_id: str) -> ExternalReviewContract | None:
        return self.store.get_review(review_id)

    def list_reviews(self, *, task_run_id: str | None = None, external_task_id: str | None = None, limit: int = 100) -> list[ExternalReviewContract]:
        return self.store.list_reviews(task_run_id=task_run_id, external_task_id=external_task_id, limit=limit)

    def adapt_and_receive_review(self, adapter_id: str, request: ExternalAdapterReviewRequest) -> dict[str, Any]:
        adapter = self.adapters.get(adapter_id)
        if adapter is None:
            raise ValueError("external_adapter_not_found")
        output: ExternalAdapterOutput = adapter.adapt_review(request)
        review = self.receive_review(output.machine_output)
        return {
            "status": "ok",
            "adapter_output": output.model_dump(),
            "review": review.model_dump(),
            "authority": "aipinho",
            "external_may_execute": False,
        }

    def list_adapters(self) -> list[dict[str, str]]:
        return self.adapters.list_adapters()

    def start_continuous_session(self, request: ContinuousCollaborationStartRequest) -> ContinuousCollaborationSession:
        task_session = self.universal_sessions.get_session(request.task_run_id)
        if task_session is None:
            raise ValueError("task_run_not_found")
        success_runtime = self._success_runtime(
            request.success_contract_id,
            maximum_iterations=request.maximum_iterations,
        )
        session = ContinuousCollaborationSession(
            provider=request.provider,
            external_conversation_id=request.external_conversation_id,
            task_run_id=request.task_run_id,
            success_contract_id=request.success_contract_id,
            expires_at=request.expires_at,
            success_runtime=success_runtime,
            retry_state={
                "current_iteration": 0,
                "maximum_iterations": success_runtime.maximum_iterations,
                "retry_count": 0,
                "reason": "session_started",
                "strategy": "Continue",
            },
            subscribed_event_types=list(request.subscribed_event_types or self._default_subscriptions()),
            metadata={
                **request.metadata,
                "authority": "aipinho",
                "external_authority": "none",
                "universal_task_session_source": True,
            },
        )
        session.memory.conversation_history.append({
            "type": "session_started",
            "task_run_id": request.task_run_id,
            "created_at": session.started_at,
        })
        return self.store.save_collaboration_session(session)

    def get_continuous_session(self, session_id: str) -> ContinuousCollaborationSession | None:
        return self.store.get_collaboration_session(session_id)

    def list_continuous_sessions(self, *, task_run_id: str | None = None, status: str | None = None, limit: int = 100) -> list[ContinuousCollaborationSession]:
        return self.store.list_collaboration_sessions(task_run_id=task_run_id, status=status, limit=limit)

    def poll_continuous_session(self, session_id: str) -> ContinuousCollaborationPollResponse | None:
        session = self.get_continuous_session(session_id)
        if session is None:
            return None
        task_session = self.universal_sessions.get_session(session.task_run_id)
        events_payload = self.universal_sessions.events(
            session.task_run_id,
            after_sequence=session.last_event_sequence,
            limit=500,
        )
        raw_events = list((events_payload or {}).get("events", []) or [])
        relevant = self._relevant_events(session, raw_events)
        if raw_events:
            session.last_event_sequence = max(int(event.get("sequence", 0) or 0) for event in raw_events)
        if relevant:
            session.observed_events.extend(relevant)
            session.memory.conversation_history.append({
                "type": "events_observed",
                "count": len(relevant),
                "last_sequence": session.last_event_sequence,
                "created_at": utc_now_iso(),
            })
        summary = self.universal_sessions.summary(session.task_run_id)
        latest_eval = self._latest_evaluation(session.session_id)
        strategy, checks = self._strategy(session, latest_eval, summary)
        session.retry_state = {
            "current_iteration": session.review_iteration,
            "maximum_iterations": session.success_runtime.maximum_iterations,
            "retry_count": session.retry_count,
            "reason": checks.get("reason", strategy),
            "strategy": strategy,
        }
        session.status = self._session_status_from_strategy(session, strategy)
        session.last_activity = utc_now_iso()
        session.success_runtime.current_iteration = session.review_iteration
        session.success_runtime.status = "completed" if strategy == "Completed" else session.status
        saved = self.store.save_collaboration_session(session)
        return ContinuousCollaborationPollResponse(
            session=saved,
            universal_task_session=task_session.model_dump() if task_session is not None else None,
            relevant_events=relevant,
            retry_strategy=strategy,
            completion_checks=checks,
        )

    def receive_success_evaluation(self, session_id: str, request: SuccessEvaluationCreateRequest) -> dict[str, Any] | None:
        session = self.get_continuous_session(session_id)
        if session is None:
            return None
        if session.review_iteration >= session.success_runtime.maximum_iterations:
            session.status = "needs_human"
            session.reason = "maximum_iterations_reached"
            session.retry_state = {
                "current_iteration": session.review_iteration,
                "maximum_iterations": session.success_runtime.maximum_iterations,
                "retry_count": session.retry_count,
                "reason": "maximum_iterations_reached",
                "strategy": "Needs Human",
            }
            self.store.save_collaboration_session(session)
            return {
                "status": "needs_human",
                "reason_code": "maximum_iterations_reached",
                "session": session.model_dump(),
            }
        delegation_id = str(request.metadata.get("delegation_id") or "") or None
        delegation_truth = DelegationTruthValidator().validate(
            " ".join([*request.blocking_findings, *request.recommendations]),
            delegation_id=delegation_id,
        )
        blocking_findings = list(dict.fromkeys([*request.blocking_findings, *delegation_truth.violations]))
        evaluation = SuccessEvaluation(
            provider=request.provider,
            session_id=session.session_id,
            task_run_id=request.task_run_id or session.task_run_id,
            external_task_id=request.external_task_id,
            status=request.status,
            acceptance_score=request.acceptance_score,
            blocking_findings=blocking_findings,
            recommendations=list(request.recommendations),
            confidence=request.confidence,
            needs_retry=request.needs_retry or bool(delegation_truth.violations),
            ready=request.ready,
            needs_human=request.needs_human,
            next_action=request.next_action,
            metadata={
                **request.metadata,
                "aipinho_authority": True,
                "external_authority": "none",
                "automatic_execution": False,
                "speaker_truth_mode": "auditor",
                "delegation_truth": delegation_truth.model_dump(),
            },
        )
        saved_eval = self.store.save_evaluation(evaluation)
        session.review_iteration += 1
        session.success_runtime.current_iteration = session.review_iteration
        session.last_evaluation_id = saved_eval.evaluation_id
        session.memory.machine_outputs.append(saved_eval.model_dump())
        session.memory.evaluations.append(saved_eval.evaluation_id)
        session.memory.conversation_history.append({
            "type": "success_evaluation_received",
            "evaluation_id": saved_eval.evaluation_id,
            "iteration": session.review_iteration,
            "created_at": saved_eval.received_at,
        })
        summary = self.universal_sessions.summary(session.task_run_id)
        strategy, checks = self._strategy(session, saved_eval, summary)
        if strategy == "Retry":
            session.retry_count += 1
        session.retry_state = {
            "current_iteration": session.review_iteration,
            "maximum_iterations": session.success_runtime.maximum_iterations,
            "retry_count": session.retry_count,
            "reason": checks.get("reason", strategy),
            "strategy": strategy,
        }
        session.status = self._session_status_from_strategy(session, strategy)
        session.last_activity = utc_now_iso()
        session.success_runtime.status = "completed" if strategy == "Completed" else session.status
        saved_session = self.store.save_collaboration_session(session)
        return {
            "status": "ok",
            "evaluation": saved_eval.model_dump(),
            "session": saved_session.model_dump(),
            "retry_strategy": strategy,
            "completion_checks": checks,
            "authority": "aipinho",
            "external_may_execute": False,
        }

    def adapt_and_receive_success_evaluation(self, adapter_id: str, session_id: str, request: ExternalAdapterEvaluationRequest) -> dict[str, Any]:
        adapter = self.adapters.get(adapter_id)
        if adapter is None:
            raise ValueError("external_adapter_not_found")
        session = self.get_continuous_session(session_id)
        if session is None:
            raise ValueError("continuous_session_not_found")
        output: ExternalAdapterEvaluationOutput = adapter.adapt_success_evaluation(
            request.model_copy(update={"session_id": session_id, "task_run_id": request.task_run_id or session.task_run_id})
        )
        result = self.receive_success_evaluation(session_id, output.machine_output)
        saved_session = self.get_continuous_session(session_id)
        if saved_session is not None:
            saved_session.memory.human_outputs.append({
                "adapter_id": output.adapter_id,
                "human_output": output.human_output,
                "created_at": utc_now_iso(),
            })
            saved_session.memory.external_messages.append({
                "adapter_id": output.adapter_id,
                "provider_output": request.provider_output[:3000],
                "created_at": utc_now_iso(),
            })
            self.store.save_collaboration_session(saved_session)
        return {
            "status": "ok",
            "adapter_output": output.model_dump(),
            "evaluation_result": result,
            "authority": "aipinho",
            "external_may_execute": False,
        }

    def list_success_evaluations(self, *, session_id: str | None = None, task_run_id: str | None = None, limit: int = 100) -> list[SuccessEvaluation]:
        return self.store.list_evaluations(session_id=session_id, task_run_id=task_run_id, limit=limit)

    def _session_payload(self, task_run_id: str | None) -> dict[str, Any] | None:
        if not task_run_id:
            return None
        session = self.universal_sessions.get_session(task_run_id)
        return session.model_dump() if session is not None else None

    def _parent_run_for_delegation(self, request: DelegationCreateRequest):
        if request.parent_run_id:
            run = self.runtime.store.get_run(request.parent_run_id)
            if run is None:
                raise ValueError("parent_task_run_not_found")
            return run
        parent = self.runtime.create_run(
            TaskRunRequest(
                source_type="direct",
                session_id=request.session_id,
                workspace=request.workspace,
                contract_type="delegation_request",
                operation_type="external_delegation",
                runtime_profile="delegation_parent",
                requested_actions=[],
                policy_decision=self._delegation_policy_snapshot(
                    request,
                    DelegationDecisionResult(decision="DELEGATE", reason_code="parent_created"),
                ),
                intent_map={
                    "source": "external_delegation_parent",
                    "provider": request.provider,
                    "objective": request.objective,
                    "authority": "aipinho",
                    "external_authority": "none",
                },
                start_immediately=False,
            )
        )
        if parent.status == "created":
            self.runtime.lifecycle.transition(parent, "waiting_delegation")
            self.runtime.store.update_run(parent)
        return parent

    def _delegation_event(self, run_id: str, event_type: str, status: str, message: str, contract: DelegationContract) -> None:
        try:
            self.runtime.events.create(
                run_id,
                event_type,
                status,
                message,
                metadata={
                    "delegation_id": contract.delegation_id,
                    "child_run_id": contract.child_run_id,
                    "executor": contract.executor,
                    "routing_policy": contract.routing_policy,
                },
            )
        except Exception:
            return

    @staticmethod
    def _delegation_policy_snapshot(request: DelegationCreateRequest, decision: DelegationDecisionResult) -> dict[str, Any]:
        return {
            "status": "allowed",
            "source": "delegation_decision_engine",
            "provider": request.provider,
            "decision": decision.decision,
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": [],
            "safe_to_preview": True,
            "safe_to_execute": False,
            "external_may_execute": False,
            "aipinho_authority": True,
        }

    def _success_runtime(self, success_contract_id: str | None, *, maximum_iterations: int) -> SuccessContractRuntime:
        contract = self.get_success_contract(success_contract_id) if success_contract_id else None
        maximum = max(1, min(int(maximum_iterations or 3), 25))
        if contract is None:
            return SuccessContractRuntime(
                success_contract_id=success_contract_id,
                goal="Acompanhar TaskRun ate conclusao governada.",
                definition_of_done="AIpinho valida a conclusao e Speaker Truth permite declarar sucesso.",
                maximum_iterations=maximum,
            )
        return SuccessContractRuntime(
            success_contract_id=contract.success_contract_id,
            goal=contract.objective,
            definition_of_done=contract.completion_definition,
            acceptance_criteria=list(contract.acceptance_criteria),
            blocking_conditions=list(contract.forbidden),
            required_evidence=list(contract.required_evidence),
            maximum_iterations=maximum,
            status=contract.status,
        )

    @staticmethod
    def _default_subscriptions() -> list[str]:
        return [
            "run_created",
            "run_queued",
            "run_waiting_input",
            "approval_required",
            "approval_preview_created",
            "patch_applied",
            "validation_completed",
            "artifact_created",
            "run_completed",
            "run_failed",
            "run_blocked",
            "run_cancelled",
        ]

    @staticmethod
    def _relevant_events(session: ContinuousCollaborationSession, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        subscribed = set(session.subscribed_event_types or [])
        if not subscribed:
            return events
        return [event for event in events if str(event.get("type") or "") in subscribed]

    def _latest_evaluation(self, session_id: str) -> SuccessEvaluation | None:
        rows = self.store.list_evaluations(session_id=session_id, limit=1)
        return rows[0] if rows else None

    def _strategy(self, session: ContinuousCollaborationSession, evaluation: SuccessEvaluation | None, summary: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
        universal_status = str((summary or {}).get("status") or "")
        validation = (summary or {}).get("validation") if isinstance((summary or {}).get("validation"), dict) else {}
        result = (summary or {}).get("result") if isinstance((summary or {}).get("result"), dict) else {}
        aipinho_validation = bool(validation.get("safe_to_report_success") or result.get("safe_to_report_success"))
        speaker_truth = bool(result.get("safe_to_report_success"))
        checks = {
            "external_ready": bool(evaluation.ready) if evaluation is not None else False,
            "aipinho_validation": aipinho_validation,
            "speaker_truth": speaker_truth,
            "universal_status": universal_status,
            "reason": "waiting_for_evaluation" if evaluation is None else "evaluation_received",
        }
        if session.status in {"cancelled", "expired"}:
            return ("Cancelled" if session.status == "cancelled" else "Expired"), checks
        if universal_status == "WAITING_APPROVAL":
            checks["reason"] = "waiting_approval"
            return "Needs Approval", checks
        if evaluation is None:
            return "Continue", checks
        if evaluation.ready and aipinho_validation and speaker_truth:
            checks["reason"] = "external_ready_and_aipinho_validated"
            return "Completed", checks
        if evaluation.needs_human:
            checks["reason"] = "external_requested_human"
            return "Needs Human", checks
        if evaluation.needs_retry or evaluation.blocking_findings or universal_status in {"FAILED", "WAITING_USER"}:
            if session.review_iteration >= session.success_runtime.maximum_iterations:
                checks["reason"] = "maximum_iterations_reached"
                return "Needs Human", checks
            checks["reason"] = "retry_recommended"
            return "Retry", checks
        return "Continue", checks

    @staticmethod
    def _session_status_from_strategy(session: ContinuousCollaborationSession, strategy: str) -> str:
        mapping = {
            "Continue": "active",
            "Retry": "retry_recommended",
            "Needs Human": "needs_human",
            "Needs Approval": "waiting_approval",
            "Completed": "completed",
            "Cancelled": "cancelled",
            "Expired": "expired",
        }
        return mapping.get(strategy, session.status)

    @staticmethod
    def _external_policy_snapshot(request: ExternalTaskCreateRequest) -> dict[str, Any]:
        return {
            "status": "allowed",
            "source": "external_agent_interface",
            "provider": request.provider,
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": [],
            "safe_to_preview": True,
            "safe_to_execute": False,
            "external_may_execute": False,
            "aipinho_authority": True,
        }
