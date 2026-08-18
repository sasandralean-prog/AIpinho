from pathlib import Path

from aipinho.services.runtime.worker_registry_service import WorkerRegistryService
from aipinho.schemas.runtime.task_run_step import TaskRunStep


def test_worker_registry_loads_contract_only_workers():
    registry = WorkerRegistryService()
    snapshot = registry.snapshot()

    assert snapshot.status == "ok"
    assert snapshot.workers
    assert "PlannerWorker" in {worker.worker_id for worker in snapshot.workers}
    assert all(worker.communicates_via_contracts for worker in snapshot.workers)
    assert all(not worker.knows_internal_implementation_of_peers for worker in snapshot.workers)


def test_worker_registry_routes_write_to_implementation_worker():
    registry = WorkerRegistryService()
    decision = registry.route_step(
        TaskRunStep(
            step_id="step_write",
            step_type="write_files",
            action="write_files",
            required=True,
            side_effect=True,
        )
    )

    assert decision.worker_id == "ImplementationWorker"
    assert decision.matched_by == "action"
    assert "workspace_write" in decision.capabilities


def test_worker_registry_routes_shell_to_security_worker():
    registry = WorkerRegistryService()
    decision = registry.route_step(
        TaskRunStep(
            step_id="step_shell",
            step_type="run_command",
            action="run_command",
            required=True,
            side_effect=True,
        )
    )

    assert decision.worker_id == "SecurityWorker"
    assert decision.matched_by == "action"
    assert "shell" in decision.capabilities


def test_worker_registry_uses_default_for_unknown_step():
    registry = WorkerRegistryService()
    decision = registry.route_step(
        TaskRunStep(
            step_id="step_unknown",
            step_type="neutral_step",
            action="neutral_step",
            required=False,
        )
    )

    assert decision.worker_id == "PlannerWorker"
    assert decision.matched_by == "default"


def test_worker_registry_reports_degraded_config(tmp_path: Path):
    config = tmp_path / "worker_registry.yaml"
    config.write_text(
        """
workers:
  - worker_id: LooseWorker
    display_name: Loose Worker
    communicates_via_contracts: false
default_worker: MissingWorker
""",
        encoding="utf-8",
    )
    registry = WorkerRegistryService(config_path=config)

    snapshot = registry.snapshot()

    assert snapshot.status == "degraded"
    assert "default_worker_missing" in snapshot.warnings
    assert "worker_not_contract_only:LooseWorker" in snapshot.warnings
