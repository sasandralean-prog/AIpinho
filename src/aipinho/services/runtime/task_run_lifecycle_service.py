from __future__ import annotations
from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file

class TaskRunLifecycleService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "runtime" / "task_run_lifecycle_policy.yaml", critical=True, root=PATHS.config_root / "runtime")

    def can_transition(self, current: str, target: str) -> bool:
        return target in set(self.policy.get("transitions", {}).get(current, []) or [])

    def transition(self, run: TaskRun, target: str) -> TaskRun:
        if run.status == target: return run
        if not self.can_transition(run.status, target):
            raise ValueError(f"invalid_task_run_transition:{run.status}->{target}")
        run.status = target  # type: ignore[assignment]
        run.revision += 1
        if target == "running" and not run.started_at: run.started_at = utc_now()
        if self.is_terminal(target): run.finished_at = utc_now()
        return run

    def is_terminal(self, status: str) -> bool:
        return status in set(self.policy.get("rules", {}).get("terminal_states", []) or [])

    def can_start(self, status: str) -> bool:
        return status in set(self.policy.get("rules", {}).get("start_requires_state", []) or [])

    def can_cancel(self, status: str) -> bool:
        return status in set(self.policy.get("rules", {}).get("cancel_allowed_from", []) or [])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_lifecycle", "states": len(self.policy.get("states", []) or []), "duplicate_start_behavior": self.policy.get("rules", {}).get("duplicate_start_behavior")}
