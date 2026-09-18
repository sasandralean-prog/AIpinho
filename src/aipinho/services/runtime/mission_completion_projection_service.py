from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.runtime.mission_completion import MissionCompletionSnapshot
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository
from aipinho.services.runtime.task_run_store import TaskRunStore


_TERMINAL_STATUSES = {
    "completed",
    "partial",
    "blocked",
    "failed",
    "cancelled",
    "expired",
}


class MissionCompletionProjectionService:
    """Rebuild a strict mission completion snapshot from canonical TaskRun state.

    This service is a projection boundary. It does not decide whether an opaque
    mission requirement is satisfied and it does not grant completion authority.
    """

    def __init__(
        self,
        store: TaskRunStore | None = None,
        *,
        outcomes: PhaseOutcomeRepository | None = None,
        missions: MissionContractService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.outcomes = outcomes or PhaseOutcomeRepository(store=self.store)
        self.missions = missions or MissionContractService()

    def project(
        self,
        *,
        mission_id: str,
        limit: int = 1000,
    ) -> MissionCompletionSnapshot:
        if not mission_id:
            return self._snapshot(
                mission_id="",
                status="missing",
                reason_codes=["MISSION_ID_REQUIRED"],
            )

        runs = sorted(
            self.store.list_runs(mission_id=mission_id, limit=limit),
            key=lambda item: (
                str(item.created_at or ""),
                str(item.run_id),
            ),
        )
        if not runs:
            return self._snapshot(
                mission_id=mission_id,
                status="missing",
                reason_codes=["MISSION_TASK_RUNS_NOT_FOUND"],
            )

        contracts = [
            run.mission_contract
            for run in runs
            if run.mission_contract is not None
            and run.mission_contract.mission_id == mission_id
        ]
        if not contracts:
            return self._snapshot(
                mission_id=mission_id,
                status="missing",
                reason_codes=["MISSION_CONTRACT_NOT_AVAILABLE"],
                task_run_ids=[run.run_id for run in runs],
                terminal_task_run_ids=[
                    run.run_id
                    for run in runs
                    if str(run.status) in _TERMINAL_STATUSES
                ],
            )

        reasons: list[str] = []
        invalid_hashes = [
            contract.authority_sha256
            for contract in contracts
            if not self.missions.verify(contract)
        ]
        if invalid_hashes:
            reasons.append("MISSION_COMPLETION_CONTRACT_AUTHORITY_INVALID")

        identity = self._identity(contracts[0])
        if any(self._identity(contract) != identity for contract in contracts[1:]):
            reasons.append("MISSION_COMPLETION_CONTRACT_IDENTITY_MISMATCH")

        completion_requirements = self._ordered_union(
            contract.completion.completion_requirements
            for contract in contracts
        )
        validation_requirements = self._ordered_union(
            contract.completion.validation_requirements
            for contract in contracts
        )
        allow_limited_completion = all(
            bool(contract.completion.allow_limited_completion)
            for contract in contracts
        )

        phase_outcomes = self.outcomes.list_for_mission(
            mission_id=mission_id,
            limit=limit,
        )
        evidence_refs = self._ordered_union(
            outcome.evidence_refs for outcome in phase_outcomes
        )
        contract_hashes = self._ordered_unique(
            [contract.authority_sha256 for contract in contracts]
        )
        revisions = sorted(
            {int(contract.revision) for contract in contracts}
        )

        return self._snapshot(
            mission_id=mission_id,
            status="invalid" if reasons else "ready",
            reason_codes=reasons,
            source_prompt_sha256=contracts[0].source_prompt_sha256,
            strategy=str(contracts[0].strategy),
            completion_requirements=completion_requirements,
            validation_requirements=validation_requirements,
            allow_limited_completion=allow_limited_completion,
            task_run_ids=[run.run_id for run in runs],
            terminal_task_run_ids=[
                run.run_id
                for run in runs
                if str(run.status) in _TERMINAL_STATUSES
            ],
            phase_outcome_run_ids=[
                outcome.producer_task_run_id for outcome in phase_outcomes
            ],
            phase_outcome_authority_sha256s=[
                outcome.authority_sha256 for outcome in phase_outcomes
            ],
            evidence_refs=evidence_refs,
            contract_authority_sha256s=contract_hashes,
            contract_revisions=revisions,
        )

    def _snapshot(
        self,
        *,
        mission_id: str,
        status: str,
        reason_codes: list[str],
        source_prompt_sha256: str | None = None,
        strategy: str | None = None,
        completion_requirements: list[str] | None = None,
        validation_requirements: list[str] | None = None,
        allow_limited_completion: bool = False,
        task_run_ids: list[str] | None = None,
        terminal_task_run_ids: list[str] | None = None,
        phase_outcome_run_ids: list[str] | None = None,
        phase_outcome_authority_sha256s: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        contract_authority_sha256s: list[str] | None = None,
        contract_revisions: list[int] | None = None,
    ) -> MissionCompletionSnapshot:
        payload: dict[str, Any] = {
            "mission_id": mission_id,
            "status": status,
            "reason_codes": self._ordered_unique(reason_codes),
            "source_prompt_sha256": source_prompt_sha256,
            "strategy": strategy,
            "completion_requirements": list(completion_requirements or []),
            "validation_requirements": list(validation_requirements or []),
            "allow_limited_completion": bool(allow_limited_completion),
            "task_run_ids": list(task_run_ids or []),
            "terminal_task_run_ids": list(terminal_task_run_ids or []),
            "phase_outcome_run_ids": list(phase_outcome_run_ids or []),
            "phase_outcome_authority_sha256s": list(
                phase_outcome_authority_sha256s or []
            ),
            "evidence_refs": list(evidence_refs or []),
            "contract_authority_sha256s": list(
                contract_authority_sha256s or []
            ),
            "contract_revisions": list(contract_revisions or []),
        }
        authority_sha256 = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return MissionCompletionSnapshot(
            **payload,
            authority_sha256=authority_sha256,
        )

    @staticmethod
    def _identity(contract) -> tuple[Any, ...]:
        return (
            contract.mission_id,
            contract.session_id,
            contract.source_message_id,
            contract.source_prompt_sha256,
            contract.objective,
            contract.semantic_context,
            str(contract.strategy),
        )

    @staticmethod
    def _ordered_union(groups) -> list[str]:
        values: list[str] = []
        for group in groups:
            values.extend(str(item) for item in group if str(item))
        return list(dict.fromkeys(values))

    @staticmethod
    def _ordered_unique(values) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
