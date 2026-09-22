from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from aipinho.schemas.governance.lifecycle import CanonicalOperationContract
from aipinho.schemas.runtime.mission_continuation import (
    MissionContinuationCandidate,
    MissionContinuationExecution,
    MissionContinuationMaterialization,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseDependencyAdmission,
    PhaseDependencyEvaluation,
)
from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.governance.policy.effective_policy_decision_service import (
    EffectivePolicyDecisionService,
)
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.runtime.mission_continuation_service import MissionContinuationService
from aipinho.services.runtime.phase_identity_service import PhaseIdentityService
from aipinho.services.runtime.phase_dependency_evaluation_service import (
    PhaseDependencyEvaluationService,
)
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class MissionPhaseCoordinatorService:
    """Materializes an admitted continuation through canonical TaskRuntime only."""

    def __init__(
        self,
        *,
        store: TaskRunStore | None = None,
        runtime: TaskRuntimeService | None = None,
        continuation: MissionContinuationService | None = None,
        dependencies: PhaseDependencyEvaluationService | None = None,
        lifecycle: TaskRunLifecycleService | None = None,
        policy: EffectivePolicyDecisionService | None = None,
        actions: ActionRegistryService | None = None,
        phases: PhaseIdentityService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.dependencies = dependencies or PhaseDependencyEvaluationService()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.policy = policy or EffectivePolicyDecisionService()
        self.actions = actions or ActionRegistryService()
        self.phases = phases or PhaseIdentityService()
        self.runtime = runtime or TaskRuntimeService(store=self.store)
        self.continuation = continuation or MissionContinuationService(
            store=self.store,
            dependencies=self.dependencies,
            lifecycle=self.lifecycle,
            phases=self.phases,
        )

    def materialize_next_run(
        self,
        *,
        previous_run_id: str,
        candidate: MissionContinuationCandidate,
        phase_outcome: PhaseOutcome | None = None,
        outstanding_completion_requirements: Iterable[str] | None = None,
    ) -> MissionContinuationMaterialization:
        decision = self.continuation.decide(
            previous_run_id=previous_run_id,
            candidate=candidate,
            phase_outcome=phase_outcome,
            outstanding_completion_requirements=outstanding_completion_requirements,
        )
        if decision.action != "continue_to_next_phase":
            return MissionContinuationMaterialization(
                status=(
                    "blocked"
                    if decision.action in {"block", "request_new_authority"}
                    else "not_applicable"
                ),
                reason_code=decision.reason_code,
                decision=decision,
                evidence_refs=list(decision.evidence_refs),
            )

        previous = self.store.get_run(previous_run_id)
        child_contract = decision.child_contract
        if previous is None or child_contract is None:
            return self._blocked(
                decision,
                "mission_continuation_materialization_state_missing",
            )

        existing = self._existing_child(previous, candidate)
        if existing is not None:
            return MissionContinuationMaterialization(
                status="materialized",
                reason_code="mission_continuation_child_already_materialized",
                decision=decision,
                child_task_run_id=existing.run_id,
                child_task_id=existing.task_id,
                child_operation_id=existing.operation_id,
                child_phase=self.phases.from_run(existing),
                reused_existing_child=True,
                dependency_evaluation=self._stored_evaluation(existing),
                dependency_admission=self._stored_admission(existing),
                evidence_refs=self._evidence_refs(existing),
            )

        outcome = phase_outcome or self.continuation.outcomes.project(
            run_id=previous.run_id
        )
        if outcome is None:
            return self._blocked(
                decision,
                "mission_continuation_phase_outcome_missing",
            )
        workspace, workspace_error = self._workspace_for_candidate(
            previous,
            child_contract,
            candidate,
        )
        if workspace_error:
            return self._blocked(decision, workspace_error)

        runtime_capabilities = self._unique(
            candidate.runtime_capabilities_required
            or candidate.required_capabilities
        )
        try:
            requested_actions = self._unique(
                [self.actions.normalize_action(action) for action in candidate.requested_actions]
            )
        except Exception as exc:
            return self._blocked(
                decision,
                f"mission_continuation_candidate_action_invalid:{exc.__class__.__name__}",
            )
        action_capabilities = self._unique(
            [
                capability
                for action in requested_actions
                for capability in [self.actions.capability_for(action)]
                if capability
            ]
        )
        if not set(action_capabilities).issubset(set(runtime_capabilities)):
            return self._blocked(
                decision,
                "mission_continuation_candidate_action_capability_mismatch",
            )
        base_intent = self._intent_map(
            previous=previous,
            candidate=candidate,
            evaluation=None,
            admission=None,
        )
        try:
            reserve_request = TaskRunRequest(
                source_type="direct",
                source_channel="mission_continuation",
                session_id=previous.session_id,
                source_message_id=child_contract.source_message_id,
                parent_task_id=previous.task_id or previous.run_id,
                mission_contract=child_contract,
                workspace=workspace,
                contract_type=candidate.contract_type,
                operation_type=candidate.operation_type,
                runtime_profile=candidate.runtime_profile,
                capabilities_required=runtime_capabilities,
                requested_actions=requested_actions,
                intent_map=base_intent,
                mode=candidate.mode,
                start_immediately=False,
            )
        except Exception as exc:
            return self._blocked(
                decision,
                f"mission_continuation_candidate_request_invalid:{exc.__class__.__name__}",
            )
        reserved = self.runtime.reserve_run(reserve_request)
        evaluation = self.continuation.evaluate_candidate_dependency(
            outcome=outcome,
            candidate=candidate,
            consumer_task_run_id=reserved.run_id,
            consumer_operation_id=str(reserved.operation_id or ""),
        )
        admission = self.dependencies.authorize(
            evaluation=evaluation,
            requirements=candidate.requirements,
            consumer_task_run_id=reserved.run_id,
            consumer_operation_id=str(reserved.operation_id or ""),
            consumer_operation_type=candidate.operation_type,
            producer_task_run_id=previous.run_id,
            producer_operation_id=previous.operation_id,
            dependency_id=candidate.dependency_id,
            producer_phase_id=outcome.phase_id,
            consumer_phase_id=candidate.phase_id,
        )
        valid, validation_reason = self.dependencies.validate_admission(
            admission,
            evaluation=evaluation,
            requirements=candidate.requirements,
            consumer_task_run_id=reserved.run_id,
            consumer_operation_id=str(reserved.operation_id or ""),
            consumer_operation_type=candidate.operation_type,
            producer_task_run_id=previous.run_id,
            producer_operation_id=previous.operation_id,
            dependency_id=candidate.dependency_id,
            producer_phase_id=outcome.phase_id,
            consumer_phase_id=candidate.phase_id,
        )
        if not admission.authorized or not valid:
            reason = str(
                validation_reason
                or admission.reason_code
                or "mission_continuation_dependency_not_admitted"
            )
            self._block_reserved(
                reserved,
                candidate=candidate,
                evaluation=evaluation,
                admission=admission.model_dump(mode="json"),
                reason=reason,
            )
            return MissionContinuationMaterialization(
                status="blocked",
                reason_code=reason,
                decision=decision,
                child_task_run_id=reserved.run_id,
                child_task_id=reserved.task_id,
                child_operation_id=reserved.operation_id,
                child_phase=candidate.phase_id,
                dependency_evaluation=evaluation,
                dependency_admission=admission.model_dump(mode="json"),
                evidence_refs=self._unique(
                    [*decision.evidence_refs, *evaluation.evidence_refs]
                ),
            )

        bound_intent = self._intent_map(
            previous=previous,
            candidate=candidate,
            evaluation=evaluation.model_dump(mode="json"),
            admission=admission.model_dump(mode="json"),
        )
        policy_snapshot = self._policy_snapshot_for_candidate(
            previous=previous,
            reserved=reserved,
            candidate=candidate,
            workspace=workspace,
            requested_actions=requested_actions,
        )
        enrich_request = reserve_request.model_copy(
            update={
                "task_id": reserved.task_id,
                "operation_id": reserved.operation_id,
                "task_run_id": reserved.run_id,
                "workspace_id": reserved.workspace_id,
                "project_id": reserved.project_id,
                "intent_map": bound_intent,
                "policy_decision": policy_snapshot,
            }
        )
        child = self.runtime.create_run(enrich_request)
        return MissionContinuationMaterialization(
            status="materialized",
            reason_code="mission_continuation_child_materialized",
            decision=decision,
            child_task_run_id=child.run_id,
            child_task_id=child.task_id,
            child_operation_id=child.operation_id,
            child_phase=child.current_phase,
            dependency_evaluation=evaluation,
            dependency_admission=admission.model_dump(mode="json"),
            evidence_refs=self._unique(
                [
                    *decision.evidence_refs,
                    *evaluation.evidence_refs,
                    f"task_run:{child.run_id}",
                ]
            ),
        )

    def execute_materialized_run(
        self,
        materialization: MissionContinuationMaterialization,
    ) -> MissionContinuationExecution:
        if materialization.status != "materialized" or not materialization.child_task_run_id:
            return MissionContinuationExecution(
                status=(
                    "not_applicable"
                    if materialization.status == "not_applicable"
                    else "blocked"
                ),
                reason_code=materialization.reason_code,
                materialization=materialization,
                child_task_run_id=materialization.child_task_run_id,
                evidence_refs=list(materialization.evidence_refs),
            )

        child = self.store.get_run(materialization.child_task_run_id)
        if child is None or child.mission_contract is None:
            return self._execution_blocked(
                materialization,
                "mission_continuation_child_run_missing",
            )
        if not child.parent_task_id:
            return self._execution_blocked(
                materialization,
                "mission_continuation_child_parent_missing",
                child=child,
            )
        parent = self.store.get_run_by_task_id(child.parent_task_id)
        if parent is None or parent.mission_contract is None:
            return self._execution_blocked(
                materialization,
                "mission_continuation_child_parent_missing",
                child=child,
            )
        try:
            self.continuation.missions.validate_child_contract(
                parent=parent.mission_contract,
                child=child.mission_contract,
            )
        except ValueError as exc:
            return self._execution_blocked(
                materialization,
                str(exc),
                child=child,
                mark_child=True,
            )

        if self.lifecycle.is_terminal(str(child.status)):
            result = self.store.get_result(child.run_id)
            successful_terminal = str(child.status) in {"completed", "partial"}
            return MissionContinuationExecution(
                status="executed" if successful_terminal else "blocked",
                reason_code=(
                    "mission_continuation_child_already_terminal"
                    if successful_terminal
                    else f"mission_continuation_child_terminal:{child.status}"
                ),
                materialization=materialization,
                child_task_run_id=child.run_id,
                child_status=str(child.status),
                result_status=str(result.status) if result is not None else None,
                reused_terminal_result=True,
                evidence_refs=self._unique(
                    [
                        *materialization.evidence_refs,
                        f"task_run:{child.run_id}",
                        *(
                            [f"task_run_result:{child.run_id}"]
                            if result is not None
                            else []
                        ),
                    ]
                ),
            )

        continuation = (
            child.intent_map.get("mission_continuation")
            if isinstance(child.intent_map.get("mission_continuation"), dict)
            else {}
        )
        requirements_value = continuation.get("phase_dependency_requirements")
        evaluation_value = continuation.get("phase_dependency_evaluation")
        admission_value = continuation.get("phase_dependency_admission")
        if not all(
            isinstance(value, dict)
            for value in (requirements_value, evaluation_value, admission_value)
        ):
            return self._execution_blocked(
                materialization,
                "mission_continuation_dependency_binding_missing",
                child=child,
                mark_child=True,
            )
        try:
            requirements = DownstreamPhaseRequirements.model_validate(requirements_value)
            evaluation = PhaseDependencyEvaluation.model_validate(evaluation_value)
            admission = PhaseDependencyAdmission.model_validate(admission_value)
        except Exception:
            return self._execution_blocked(
                materialization,
                "mission_continuation_dependency_binding_invalid",
                child=child,
                mark_child=True,
            )

        previous_phase = str(continuation.get("previous_phase") or "")
        next_phase = str(
            continuation.get("next_phase")
            or self.phases.from_run(child)
            or ""
        )
        dependency_id = str(continuation.get("dependency_id") or "")
        valid, validation_reason = self.dependencies.validate_admission(
            admission,
            evaluation=evaluation,
            requirements=requirements,
            consumer_task_run_id=child.run_id,
            consumer_operation_id=str(child.operation_id or ""),
            consumer_operation_type=str(child.operation_type or ""),
            producer_task_run_id=parent.run_id,
            producer_operation_id=parent.operation_id,
            dependency_id=dependency_id,
            producer_phase_id=previous_phase,
            consumer_phase_id=next_phase,
        )
        if not admission.authorized or not valid:
            return self._execution_blocked(
                materialization,
                str(
                    validation_reason
                    or admission.reason_code
                    or "mission_continuation_dependency_admission_invalid"
                ),
                child=child,
                mark_child=True,
            )

        started, result = self.runtime.start(child.run_id)
        blocked_statuses = {"blocked", "failed", "cancelled", "expired"}
        return MissionContinuationExecution(
            status=(
                "blocked"
                if str(started.status) in blocked_statuses
                else "executed"
            ),
            reason_code=(
                f"mission_continuation_taskruntime:{started.status}"
                if str(started.status) in blocked_statuses
                else "mission_continuation_child_started_via_taskruntime"
            ),
            materialization=materialization,
            child_task_run_id=started.run_id,
            child_status=str(started.status),
            result_status=str(result.status) if result is not None else None,
            evidence_refs=self._unique(
                [
                    *materialization.evidence_refs,
                    f"task_run:{started.run_id}",
                    *(
                        [f"task_run_result:{started.run_id}"]
                        if result is not None
                        else []
                    ),
                ]
            ),
        )

    def _existing_child(self, previous, candidate):
        parent_refs = {str(previous.task_id or ""), str(previous.run_id)}
        for run in self.store.list_runs(
            session_id=previous.session_id,
            limit=1000,
        ):
            if str(run.parent_task_id or "") not in parent_refs:
                continue
            continuation = (
                run.intent_map.get("mission_continuation")
                if isinstance(run.intent_map.get("mission_continuation"), dict)
                else {}
            )
            if str(continuation.get("candidate_id") or "") == candidate.candidate_id:
                return self.store.get_run(run.run_id) or run
        return None

    def _workspace_for_candidate(self, previous, contract, candidate):
        resources = {item.resource_id: item for item in contract.local_resources}
        if candidate.workspace_resource_id:
            resource = resources.get(candidate.workspace_resource_id)
            if resource is None or not resource.locator:
                return None, "mission_continuation_workspace_resource_missing"
            return resource.locator, None
        if previous.workspace:
            for resource in resources.values():
                if resource.locator and self._same_path(resource.locator, previous.workspace):
                    return resource.locator, None
        located = [item.locator for item in resources.values() if item.locator]
        if len(located) == 1:
            return located[0], None
        return None, None

    def _policy_snapshot_for_candidate(
        self,
        *,
        previous,
        reserved,
        candidate,
        workspace: str | None,
        requested_actions: list[str],
    ) -> dict:
        side_effect = any(
            self.actions.is_side_effect(action) for action in requested_actions
        )
        contract = CanonicalOperationContract(
            operation_id=str(reserved.operation_id or ""),
            session_id=previous.session_id,
            source_channel="mission_continuation",
            intent_type=str(
                previous.intent_map.get("intent_type") or candidate.operation_type
            ),
            operation_type=candidate.operation_type,
            contract_type=candidate.contract_type,
            runtime_profile=str(candidate.runtime_profile or ""),
            requires_task=True,
            read_only=not side_effect,
            artifact_generation=False,
            workspace_mutation=side_effect,
            requested_actions=list(requested_actions),
            workspace_path=workspace,
            risk_level="medium" if side_effect else "low",
            trace=[
                {
                    "stage": "mission_continuation_policy_contract",
                    "source": "MissionPhaseCoordinatorService",
                    "candidate_id": candidate.candidate_id,
                }
            ],
        )
        decision = self.policy.resolve(contract)
        payload = decision.model_dump(mode="json")
        permission = decision.permission.value
        payload["status"] = permission
        payload["policy_status"] = permission
        payload["approval_required_for"] = (
            list(decision.ask_actions) if decision.requires_approval else []
        )
        return payload

    def _intent_map(self, *, previous, candidate, evaluation, admission):
        previous_continuation = (
            previous.intent_map.get("mission_continuation")
            if isinstance(previous.intent_map.get("mission_continuation"), dict)
            else {}
        )
        try:
            previous_depth = max(
                0,
                int(previous_continuation.get("depth") or 0),
            )
        except (TypeError, ValueError):
            previous_depth = 0
        lineage = [
            str(item)
            for item in list(previous_continuation.get("lineage") or [])
            if str(item)
        ]
        lineage = self._unique([*lineage, previous.run_id])
        previous_phase = self.phases.from_run(previous)
        phase_lineage = self._unique(
            [
                *list(previous_continuation.get("phase_lineage") or []),
                *([str(previous_phase)] if previous_phase else []),
                candidate.phase_id,
            ]
        )
        history = [
            dict(item)
            for item in list(previous_continuation.get("history") or [])
            if isinstance(item, dict)
        ]
        history.append(
            {
                "candidate_id": candidate.candidate_id,
                "phase_id": candidate.phase_id,
                "operation_type": candidate.operation_type,
                "contract_type": candidate.contract_type,
                "runtime_profile": candidate.runtime_profile,
                "requested_actions": list(candidate.requested_actions),
                "required_capabilities": list(candidate.required_capabilities),
                "runtime_capabilities_required": list(
                    candidate.runtime_capabilities_required
                ),
            }
        )
        payload = {
            "candidate_id": candidate.candidate_id,
            "planner_ref": candidate.planner_ref,
            "dependency_id": candidate.dependency_id,
            "previous_run_id": previous.run_id,
            "previous_task_id": previous.task_id,
            "previous_phase": previous_phase,
            "next_phase": candidate.phase_id,
            "depth": previous_depth + 1,
            "lineage": lineage,
            "phase_lineage": phase_lineage,
            "history": history,
            "phase_dependency_requirements": candidate.requirements.model_dump(
                mode="json"
            ),
        }
        repair = (
            dict(candidate.metadata.get("evidence_repair") or {})
            if isinstance(candidate.metadata, dict)
            and isinstance(candidate.metadata.get("evidence_repair"), dict)
            else {}
        )
        if repair.get("required"):
            payload["evidence_repair"] = repair
        if evaluation is not None:
            payload["phase_dependency_evaluation"] = evaluation
        if admission is not None:
            payload["phase_dependency_admission"] = admission
        inherited_semantics = {
            key: previous.intent_map[key]
            for key in (
                "semantic_intent_graph",
                "future_side_effect_intent",
                "mission_execution_strategy",
                "completion_requirements",
                "validation_requirements",
                "allow_limited_completion",
            )
            if key in previous.intent_map
        }
        return {
            **inherited_semantics,
            "intent_type": str(
                previous.intent_map.get("intent_type")
                or candidate.operation_type
            ),
            "operation_type": candidate.operation_type,
            "current_phase": candidate.phase_id,
            "phase_id": candidate.phase_id,
            "mission_phase": candidate.phase_id,
            "mission_continuation": payload,
        }

    def _block_reserved(
        self,
        run,
        *,
        candidate,
        evaluation,
        admission,
        reason: str,
    ) -> None:
        continuation = self._intent_map(
            previous=self.store.get_run_by_task_id(run.parent_task_id) or run,
            candidate=candidate,
            evaluation=evaluation.model_dump(mode="json"),
            admission=admission,
        )
        run.intent_map = continuation
        if self.lifecycle.can_transition(str(run.status), "blocked"):
            run = self.lifecycle.transition(run, "blocked")
        run.blocked_reasons = self._unique([*run.blocked_reasons, reason])
        self.store.update_run(run)

    @staticmethod
    def _stored_evaluation(run):
        continuation = (
            run.intent_map.get("mission_continuation")
            if isinstance(run.intent_map.get("mission_continuation"), dict)
            else {}
        )
        value = continuation.get("phase_dependency_evaluation")
        if not isinstance(value, dict):
            return None
        from aipinho.schemas.runtime.phase_dependency_evaluation import (
            PhaseDependencyEvaluation,
        )
        return PhaseDependencyEvaluation.model_validate(value)

    @staticmethod
    def _stored_admission(run):
        continuation = (
            run.intent_map.get("mission_continuation")
            if isinstance(run.intent_map.get("mission_continuation"), dict)
            else {}
        )
        value = continuation.get("phase_dependency_admission")
        return dict(value) if isinstance(value, dict) else None

    def _evidence_refs(self, run) -> list[str]:
        evaluation = self._stored_evaluation(run)
        return self._unique(
            [
                *(evaluation.evidence_refs if evaluation is not None else []),
                f"task_run:{run.run_id}",
            ]
        )

    def _execution_blocked(
        self,
        materialization: MissionContinuationMaterialization,
        reason: str,
        *,
        child=None,
        mark_child: bool = False,
    ) -> MissionContinuationExecution:
        if child is not None and mark_child:
            if self.lifecycle.can_transition(str(child.status), "blocked"):
                child = self.lifecycle.transition(child, "blocked")
            child.blocked_reasons = self._unique([*child.blocked_reasons, reason])
            self.store.update_run(child)
        return MissionContinuationExecution(
            status="blocked",
            reason_code=reason,
            materialization=materialization,
            child_task_run_id=child.run_id if child is not None else materialization.child_task_run_id,
            child_status=str(child.status) if child is not None else None,
            evidence_refs=self._unique(
                [
                    *materialization.evidence_refs,
                    *([f"task_run:{child.run_id}"] if child is not None else []),
                ]
            ),
        )

    @staticmethod
    def _same_path(left: str, right: str) -> bool:
        return os.path.normcase(
            str(Path(left).expanduser().resolve(strict=False))
        ) == os.path.normcase(
            str(Path(right).expanduser().resolve(strict=False))
        )

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))

    @staticmethod
    def _blocked(decision, reason: str) -> MissionContinuationMaterialization:
        return MissionContinuationMaterialization(
            status="blocked",
            reason_code=reason,
            decision=decision,
            evidence_refs=list(decision.evidence_refs),
        )
