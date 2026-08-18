from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable

from aipinho.core.paths import PATHS
from aipinho.schemas.memory.operational_memory import (
    DecisionMemory,
    ExecutionMemory,
    FailureMemory,
    LearningMemory,
    OperationalMemoryEvidence,
    OperationalMemoryRecord,
    OperationalMemorySnapshot,
    RecoveryMemory,
    StrategyMemory,
)
from aipinho.schemas.runtime.task_run import TaskRun


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,;]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
]


class OperationalMemoryService:
    """Runtime-scoped operational memory, separate from curated/chat memory."""

    def __init__(self, root: Path | None = None) -> None:
        configured = os.getenv("AIPINHO_OPERATIONAL_MEMORY_ROOT")
        self.root = root or (Path(configured) if configured else PATHS.project_root / "data" / "runtime" / "operational_memory")
        self.root.mkdir(parents=True, exist_ok=True)

    def capture_task_run(self, run: TaskRun, *, trigger: str) -> OperationalMemorySnapshot:
        records = self._build_records(run, trigger=trigger)
        snapshot = OperationalMemorySnapshot(run_id=run.run_id, records=records)
        self._write_snapshot(snapshot)
        return snapshot

    def get_snapshot(self, run_id: str) -> OperationalMemorySnapshot | None:
        path = self._path_for_run(run_id)
        if not path.exists():
            return None
        return OperationalMemorySnapshot.model_validate_json(path.read_text(encoding="utf-8"))

    def list_for_run(self, run_id: str) -> list[OperationalMemoryRecord]:
        snapshot = self.get_snapshot(run_id)
        return snapshot.records if snapshot else []

    def search(self, *, workspace: str | None = None, memory_type: str | None = None, limit: int = 50) -> list[OperationalMemoryRecord]:
        records: list[OperationalMemoryRecord] = []
        for path in sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            snapshot = OperationalMemorySnapshot.model_validate_json(path.read_text(encoding="utf-8"))
            for record in snapshot.records:
                if workspace and record.workspace != workspace:
                    continue
                if memory_type and record.memory_type != memory_type:
                    continue
                records.append(record)
                if len(records) >= limit:
                    return records
        return records

    def _build_records(self, run: TaskRun, *, trigger: str) -> list[OperationalMemoryRecord]:
        records: list[OperationalMemoryRecord] = [
            self._decision_record(run, trigger=trigger),
            self._strategy_record(run, trigger=trigger),
            self._execution_record(run, trigger=trigger),
        ]
        if run.status in {"blocked", "failed", "cancelled"} or run.blocked_reasons:
            records.append(self._failure_record(run, trigger=trigger))
            records.append(self._recovery_record(run, trigger=trigger))
        if run.status in {"completed", "partial", "blocked", "failed", "cancelled"}:
            records.append(self._learning_record(run, trigger=trigger))
        return records

    def _decision_record(self, run: TaskRun, *, trigger: str) -> DecisionMemory:
        return DecisionMemory(
            title="TaskRun operation decision",
            summary=self._clean(
                f"{run.operation_type or 'unknown'} selected with contract {run.contract_type or 'unknown'} and runtime profile {run.runtime_profile or 'unknown'}."
            ),
            decision=run.operation_type or run.contract_type or "unknown",
            source_run_id=run.run_id,
            session_id=run.session_id,
            workspace=self._clean(run.workspace),
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            runtime_profile=run.runtime_profile,
            outcome=run.status,
            evidence=self._evidence(run),
            tags=["operational", "decision", trigger],
        )

    def _strategy_record(self, run: TaskRun, *, trigger: str) -> StrategyMemory:
        steps = [step.step_type for step in run.plan.steps]
        return StrategyMemory(
            title="TaskRun execution strategy",
            summary=self._clean(f"Plan contains {len(steps)} governed steps: {', '.join(steps[:8])}."),
            strategy=run.runtime_profile or run.contract_type or "unknown",
            source_run_id=run.run_id,
            session_id=run.session_id,
            workspace=self._clean(run.workspace),
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            runtime_profile=run.runtime_profile,
            outcome=run.status,
            evidence=self._evidence(run),
            reusable_when=[run.contract_type] if run.contract_type else [],
            tags=["operational", "strategy", trigger],
            metadata_sanitized={"step_count": len(steps), "steps": steps},
        )

    def _execution_record(self, run: TaskRun, *, trigger: str) -> ExecutionMemory:
        executed_steps = [step.step_id for step in run.plan.steps if step.status in {"completed", "partial", "blocked", "failed", "cancelled"}]
        graph_status = run.execution_graph.status if run.execution_graph else None
        return ExecutionMemory(
            title="TaskRun execution lifecycle",
            summary=self._clean(f"Run status is {run.status}; execution graph status is {graph_status or 'missing'}."),
            executed_steps=executed_steps,
            source_run_id=run.run_id,
            session_id=run.session_id,
            workspace=self._clean(run.workspace),
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            runtime_profile=run.runtime_profile,
            outcome=run.status,
            evidence=self._evidence(run),
            tags=["operational", "execution", trigger],
            metadata_sanitized={
                "graph_id": run.execution_graph.graph_id if run.execution_graph else None,
                "graph_status": graph_status,
                "executed_steps": executed_steps,
            },
        )

    def _failure_record(self, run: TaskRun, *, trigger: str) -> FailureMemory:
        reason = self._first_non_empty(run.blocked_reasons) or (
            run.block_cause.block_reason_code if run.block_cause else None
        ) or run.status
        return FailureMemory(
            title="TaskRun failure or block pattern",
            summary=self._clean(f"Run ended or paused with reason {reason}."),
            failure_code=reason,
            source_run_id=run.run_id,
            session_id=run.session_id,
            workspace=self._clean(run.workspace),
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            runtime_profile=run.runtime_profile,
            outcome=run.status,
            evidence=self._evidence(run),
            avoid_when=list(run.blocked_reasons),
            tags=["operational", "failure", trigger],
        )

    def _recovery_record(self, run: TaskRun, *, trigger: str) -> RecoveryMemory:
        safe_alternatives = []
        if run.block_cause:
            safe_alternatives = list(run.block_cause.safe_alternatives)
        action = self._first_non_empty(safe_alternatives) or "inspect_task_run_trace"
        return RecoveryMemory(
            title="TaskRun recovery path",
            summary=self._clean(f"Recommended recovery action: {action}."),
            recovery_action=action,
            source_run_id=run.run_id,
            session_id=run.session_id,
            workspace=self._clean(run.workspace),
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            runtime_profile=run.runtime_profile,
            outcome=run.status,
            evidence=self._evidence(run),
            reusable_when=safe_alternatives,
            tags=["operational", "recovery", trigger],
        )

    def _learning_record(self, run: TaskRun, *, trigger: str) -> LearningMemory:
        lesson = "runtime_completed" if run.status == "completed" else f"runtime_{run.status}"
        return LearningMemory(
            title="TaskRun operational lesson",
            summary=self._clean(f"Outcome {run.status} recorded for {run.contract_type or 'unknown'} using {run.runtime_profile or 'unknown'}."),
            lesson=lesson,
            source_run_id=run.run_id,
            session_id=run.session_id,
            workspace=self._clean(run.workspace),
            operation_type=run.operation_type,
            contract_type=run.contract_type,
            runtime_profile=run.runtime_profile,
            outcome=run.status,
            evidence=self._evidence(run),
            reusable_when=[run.runtime_profile] if run.runtime_profile else [],
            tags=["operational", "learning", trigger],
        )

    def _evidence(self, run: TaskRun) -> list[OperationalMemoryEvidence]:
        evidence = [
            OperationalMemoryEvidence(
                evidence_type="task_run",
                ref_id=run.run_id,
                summary=f"TaskRun status {run.status}.",
            ),
            OperationalMemoryEvidence(
                evidence_type="task_run_plan",
                ref_id=run.plan.plan_id,
                summary=f"Plan status {run.plan.status}.",
                metadata={"steps": len(run.plan.steps)},
            ),
        ]
        if run.execution_graph:
            evidence.append(
                OperationalMemoryEvidence(
                    evidence_type="execution_graph",
                    ref_id=run.execution_graph.graph_id,
                    summary=f"ExecutionGraph status {run.execution_graph.status}.",
                    metadata={
                        "nodes": len(run.execution_graph.nodes),
                        "edges": len(run.execution_graph.edges),
                    },
                )
            )
        if run.block_cause:
            evidence.append(
                OperationalMemoryEvidence(
                    evidence_type="block_cause",
                    ref_id=run.block_cause.block_id,
                    summary=run.block_cause.block_reason_code,
                )
            )
        return evidence

    def _write_snapshot(self, snapshot: OperationalMemorySnapshot) -> None:
        path = self._path_for_run(snapshot.run_id)
        payload = snapshot.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _path_for_run(self, run_id: str) -> Path:
        safe_run_id = re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)
        return self.root / f"{safe_run_id}.json"

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value)
        for pattern in SECRET_PATTERNS:
            cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned

    def _first_non_empty(self, values: Iterable[str] | None) -> str | None:
        if not values:
            return None
        for value in values:
            if value:
                return value
        return None
