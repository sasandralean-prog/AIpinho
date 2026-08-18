from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.runtime.worker_contract import (
    WorkerContract,
    WorkerRegistrySnapshot,
    WorkerRouteDecision,
)
from aipinho.utils.yaml_loader import load_yaml_file


class WorkerRegistryService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "worker_registry.yaml"
        self.config_root = self.config_path.parent if config_path else PATHS.config_root
        self._snapshot: WorkerRegistrySnapshot | None = None

    def snapshot(self) -> WorkerRegistrySnapshot:
        if self._snapshot is None:
            self._snapshot = self._load()
        return self._snapshot

    def route_step(self, step: TaskRunStep) -> WorkerRouteDecision:
        snapshot = self.snapshot()
        action = str(step.action or "")
        step_type = str(step.step_type or "")
        active_workers = [worker for worker in snapshot.workers if worker.status == "active"]
        for worker in active_workers:
            if action and action in worker.accepted_actions:
                return self._decision(worker, matched_by="action", reason=f"action:{action}", step=step, confidence="high")
        haystack = f"{action} {step_type}".casefold()
        for worker in active_workers:
            for keyword in worker.accepted_step_keywords:
                if keyword and keyword.casefold() in haystack:
                    return self._decision(worker, matched_by="keyword", reason=f"keyword:{keyword}", step=step, confidence="medium")
        default = self._find_worker(snapshot.default_worker, active_workers) or self._find_worker("PlannerWorker", active_workers)
        if default is None:
            return WorkerRouteDecision(
                worker_id="PlannerWorker",
                matched_by="default",
                reason="worker_registry_empty_default",
                confidence="low",
                action=action,
                step_type=step_type,
                warnings=["worker_registry_default_missing"],
            )
        return self._decision(default, matched_by="default", reason="default_worker", step=step, confidence="low")

    def _load(self) -> WorkerRegistrySnapshot:
        raw = load_yaml_file(self.config_path, critical=True, root=self.config_root)
        workers = [WorkerContract.model_validate(item) for item in raw.get("workers", [])]
        default_worker = str(raw.get("default_worker") or "PlannerWorker")
        warnings = self._validate(workers, default_worker)
        return WorkerRegistrySnapshot(
            status="degraded" if warnings else "ok",
            workers=workers,
            default_worker=default_worker,
            warnings=warnings,
        )

    def _validate(self, workers: list[WorkerContract], default_worker: str) -> list[str]:
        warnings: list[str] = []
        worker_ids = [worker.worker_id for worker in workers]
        if len(worker_ids) != len(set(worker_ids)):
            warnings.append("duplicate_worker_id")
        if default_worker not in worker_ids:
            warnings.append("default_worker_missing")
        for worker in workers:
            if not worker.communicates_via_contracts:
                warnings.append(f"worker_not_contract_only:{worker.worker_id}")
            if worker.knows_internal_implementation_of_peers:
                warnings.append(f"worker_peer_internal_dependency:{worker.worker_id}")
        return warnings

    def _find_worker(self, worker_id: str, workers: list[WorkerContract]) -> WorkerContract | None:
        for worker in workers:
            if worker.worker_id == worker_id:
                return worker
        return None

    def _decision(
        self,
        worker: WorkerContract,
        *,
        matched_by: str,
        reason: str,
        step: TaskRunStep,
        confidence: str,
    ) -> WorkerRouteDecision:
        return WorkerRouteDecision(
            worker_id=worker.worker_id,
            matched_by=matched_by,
            reason=reason,
            confidence=confidence,
            action=step.action,
            step_type=step.step_type,
            capabilities=list(worker.capabilities),
            output_contracts=list(worker.output_contracts),
        )
