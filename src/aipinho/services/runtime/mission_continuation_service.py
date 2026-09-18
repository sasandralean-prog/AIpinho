from __future__ import annotations

from typing import Iterable

from aipinho.schemas.runtime.mission_continuation import (
    MissionContinuationCandidate,
    MissionContinuationDecision,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import PhaseDependencySnapshot
from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.phase_dependency_evaluation_service import (
    PhaseDependencyEvaluationService,
)
from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore


_BLOCKING_TRUTH = {"blocked", "failed", "cancelled", "expired"}


class MissionContinuationService:
    """Evaluates mission continuation without planning or executing the next phase."""

    def __init__(
        self,
        *,
        store: TaskRunStore | None = None,
        outcomes: PhaseOutcomeRepository | None = None,
        dependencies: PhaseDependencyEvaluationService | None = None,
        missions: MissionContractService | None = None,
        lifecycle: TaskRunLifecycleService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.outcomes = outcomes or PhaseOutcomeRepository(store=self.store)
        self.dependencies = dependencies or PhaseDependencyEvaluationService()
        self.missions = missions or MissionContractService()
        self.lifecycle = lifecycle or TaskRunLifecycleService()

    def decide(
        self,
        *,
        previous_run_id: str,
        candidate: MissionContinuationCandidate | None = None,
        phase_outcome: PhaseOutcome | None = None,
        outstanding_completion_requirements: Iterable[str] | None = None,
    ) -> MissionContinuationDecision:
        outstanding = self._unique(outstanding_completion_requirements or [])
        run = self.store.get_run(previous_run_id)
        if run is None or run.mission_contract is None:
            return self._decision(
                "block",
                "mission_continuation_previous_run_missing",
                previous_run_id=previous_run_id,
                outstanding=outstanding,
            )
        contract = run.mission_contract
        common = {
            "mission_id": contract.mission_id,
            "strategy": contract.strategy,
            "previous_run_id": run.run_id,
            "previous_phase": self._phase_id(run),
            "outstanding": outstanding,
        }
        if not self.missions.verify(contract):
            return self._decision(
                "block",
                "mission_continuation_mission_contract_invalid",
                **common,
            )
        if not self.lifecycle.is_terminal(str(run.status)):
            return self._decision(
                "block",
                "mission_continuation_previous_run_not_terminal",
                **common,
            )

        outcome = phase_outcome or self.outcomes.project(run_id=run.run_id)
        if outcome is None:
            return self._decision(
                "block",
                "mission_continuation_phase_outcome_missing",
                **common,
            )
        binding_error = self._outcome_binding_error(run, outcome)
        if binding_error:
            return self._decision("block", binding_error, **common)
        if self._outcome_truth_blocks(outcome):
            return self._decision(
                "block",
                "mission_continuation_upstream_truth_blocked",
                evidence_refs=outcome.evidence_refs,
                **common,
            )

        if contract.strategy == "single_operation":
            return self._decision(
                "block" if outstanding else "complete",
                (
                    "mission_continuation_single_operation_has_outstanding_requirements"
                    if outstanding
                    else "mission_continuation_single_operation_complete"
                ),
                evidence_refs=outcome.evidence_refs,
                **common,
            )
        if candidate is None:
            return self._decision(
                "complete" if not outstanding else "block",
                (
                    "mission_continuation_no_outstanding_requirements"
                    if not outstanding
                    else "mission_continuation_candidate_required_for_outstanding_work"
                ),
                evidence_refs=outcome.evidence_refs,
                **common,
            )

        candidate_error = self._candidate_contract_error(candidate)
        if candidate_error:
            return self._decision(
                "block",
                candidate_error,
                candidate=candidate,
                evidence_refs=outcome.evidence_refs,
                **common,
            )
        resource_error, local_resources, remote_resources = self._candidate_resources(
            contract,
            candidate,
        )
        if resource_error:
            return self._decision(
                "block",
                resource_error,
                candidate=candidate,
                evidence_refs=outcome.evidence_refs,
                **common,
            )

        required_capabilities = self._unique(
            [
                *candidate.required_capabilities,
                *candidate.requirements.required_capabilities,
            ]
        )
        missing_requested = sorted(
            set(required_capabilities) - set(contract.authority.requested_capabilities)
        )
        missing_authorized = sorted(
            set(required_capabilities) - set(contract.authority.authorized_capabilities)
        )
        if missing_requested or missing_authorized:
            return self._decision(
                "request_new_authority",
                "mission_continuation_authority_gap",
                candidate=candidate,
                authority_gap=self._unique([*missing_requested, *missing_authorized]),
                evidence_refs=outcome.evidence_refs,
                **common,
            )

        evaluation = self.evaluate_candidate_dependency(
            outcome=outcome,
            candidate=candidate,
            consumer_task_run_id=f"candidate:{candidate.candidate_id}",
            consumer_operation_id=f"candidate_operation:{candidate.candidate_id}",
        )
        if evaluation.decision not in {"ADMITTED", "ADMITTED_WITH_CONSTRAINTS"}:
            return self._decision(
                "block",
                (
                    evaluation.reason_codes[0]
                    if evaluation.reason_codes
                    else "mission_continuation_dependency_not_admitted"
                ),
                candidate=candidate,
                evaluation=evaluation,
                constraints=evaluation.constraints,
                evidence_refs=self._unique([*outcome.evidence_refs, *evaluation.evidence_refs]),
                **common,
            )
        try:
            child = self.missions.narrowed_child(
                contract,
                requested_capabilities=required_capabilities,
                authorized_capabilities=required_capabilities,
                local_resources=local_resources,
                remote_resources=remote_resources,
                additional_constraints=[],
            )
        except ValueError as exc:
            return self._decision(
                "block",
                str(exc),
                candidate=candidate,
                evaluation=evaluation,
                constraints=evaluation.constraints,
                evidence_refs=self._unique([*outcome.evidence_refs, *evaluation.evidence_refs]),
                **common,
            )

        if contract.strategy == "staged":
            return self._decision(
                "await_existing_authority",
                "mission_continuation_staged_boundary",
                candidate=candidate,
                child_contract=child,
                evaluation=evaluation,
                constraints=evaluation.constraints,
                evidence_refs=self._unique([*outcome.evidence_refs, *evaluation.evidence_refs]),
                **common,
            )

        return self._decision(
            "continue_to_next_phase",
            "mission_continuation_existing_authority_and_evidence_allow",
            candidate=candidate,
            child_contract=child,
            evaluation=evaluation,
            constraints=evaluation.constraints,
            evidence_refs=self._unique([*outcome.evidence_refs, *evaluation.evidence_refs]),
            **common,
        )
    def evaluate_candidate_dependency(
        self,
        *,
        outcome: PhaseOutcome,
        candidate: MissionContinuationCandidate,
        consumer_task_run_id: str,
        consumer_operation_id: str,
    ):
        snapshot = self._dependency_snapshot(outcome, candidate)
        return self.dependencies.evaluate(
            snapshot=snapshot,
            requirements=candidate.requirements,
            consumer_task_run_id=consumer_task_run_id,
            consumer_operation_id=consumer_operation_id,
            consumer_operation_type=candidate.operation_type,
        )

    def _candidate_contract_error(self, candidate: MissionContinuationCandidate) -> str | None:
        requirements = candidate.requirements
        if not candidate.planner_ref.strip():
            return "mission_continuation_planner_ref_missing"
        if requirements.consumer_phase_id != candidate.phase_id:
            return "mission_continuation_candidate_phase_requirement_mismatch"
        if requirements.operation_type != candidate.operation_type:
            return "mission_continuation_candidate_operation_requirement_mismatch"
        return None

    def _candidate_resources(self, contract, candidate):
        local_by_id = {item.resource_id: item for item in contract.local_resources}
        remote_by_id = {item.resource_id: item for item in contract.remote_resources}
        local_ids = candidate.local_resource_ids or list(local_by_id)
        remote_ids = candidate.remote_resource_ids or list(remote_by_id)
        if not set(local_ids).issubset(local_by_id):
            return "mission_continuation_local_resource_out_of_scope", [], []
        if (
            candidate.workspace_resource_id
            and candidate.workspace_resource_id not in set(local_ids)
        ):
            return "mission_continuation_workspace_resource_out_of_scope", [], []
        if not set(remote_ids).issubset(remote_by_id):
            return "mission_continuation_remote_resource_out_of_scope", [], []
        return (
            None,
            [local_by_id[item] for item in local_ids],
            [remote_by_id[item] for item in remote_ids],
        )

    def _dependency_snapshot(
        self,
        outcome: PhaseOutcome,
        candidate: MissionContinuationCandidate,
    ) -> PhaseDependencySnapshot:
        dependency = dict(outcome.phase_dependency or {})
        status = str(dependency.get("status") or self._dependency_status(outcome.result_status))
        return PhaseDependencySnapshot(
            dependency_id=candidate.dependency_id,
            producer_task_run_id=outcome.producer_task_run_id,
            producer_operation_id=outcome.producer_operation_id,
            producer_phase_id=outcome.phase_id,
            upstream_result_ref=outcome.result_ref,
            dependency_status=status,
            evidence_refs=list(outcome.evidence_refs),
            limitations=list(outcome.limitations),
            required_disclosures=list(outcome.required_disclosures),
            missing_truth=list(outcome.missing_truth),
            risk_constraints=list(outcome.risk_constraints),
            allowed_downstream_uses=list(dependency.get("allowed_downstream_uses") or []),
            forbidden_downstream_uses=list(dependency.get("forbidden_downstream_uses") or []),
            forbidden_claims=list(dependency.get("forbidden_downstream_claims") or []),
            use_safety=dict(outcome.use_safety),
            semantic_properties=dict(outcome.semantic_properties),
        )

    def _outcome_binding_error(self, run, outcome: PhaseOutcome) -> str | None:
        if outcome.producer_task_run_id != run.run_id:
            return "mission_continuation_outcome_run_mismatch"
        phase = self._phase_id(run)
        if phase and outcome.phase_id != phase:
            return "mission_continuation_outcome_phase_mismatch"
        return None

    def _outcome_truth_blocks(self, outcome: PhaseOutcome) -> bool:
        runtime_truth_status = str(
            outcome.semantic_properties.get("runtime_truth_status") or ""
        )
        dependency_status = str((outcome.phase_dependency or {}).get("status") or "")
        return (
            runtime_truth_status in _BLOCKING_TRUTH
            or dependency_status == "blocked"
            or outcome.result_status in _BLOCKING_TRUTH
        )

    @staticmethod
    def _dependency_status(result_status: str) -> str:
        if result_status == "completed":
            return "satisfied"
        if result_status in {"partial", "completed_with_limitations"}:
            return "satisfied_with_limitations"
        return result_status
    @staticmethod
    def _phase_id(run) -> str | None:
        value = (
            run.intent_map.get("phase_id")
            or run.intent_map.get("mission_phase")
            or run.current_phase
            or run.bootstrap_context.get("phase_id")
        )
        return str(value) if value else None

    def _decision(
        self,
        action: str,
        reason_code: str,
        *,
        mission_id: str | None = None,
        strategy: str | None = None,
        previous_run_id: str | None = None,
        previous_phase: str | None = None,
        candidate: MissionContinuationCandidate | None = None,
        child_contract=None,
        evaluation=None,
        authority_gap: Iterable[str] | None = None,
        outstanding: Iterable[str] | None = None,
        constraints: Iterable[str] | None = None,
        evidence_refs: Iterable[str] | None = None,
    ) -> MissionContinuationDecision:
        return MissionContinuationDecision(
            action=action,
            reason_code=reason_code,
            mission_id=mission_id,
            strategy=strategy,
            previous_run_id=previous_run_id,
            previous_phase=previous_phase,
            next_phase=candidate.phase_id if candidate else None,
            candidate_id=candidate.candidate_id if candidate else None,
            planner_ref=candidate.planner_ref if candidate else None,
            child_contract=child_contract,
            dependency_evaluation=evaluation,
            authority_gap=self._unique(authority_gap or []),
            outstanding_completion_requirements=self._unique(outstanding or []),
            constraints=self._unique(constraints or []),
            evidence_refs=self._unique(evidence_refs or []),
            trace=[
                {
                    "stage": "mission_continuation_decision",
                    "action": action,
                    "reason_code": reason_code,
                }
            ],
        )

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
