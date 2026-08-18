from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


OperationalMemoryType = Literal[
    "decision",
    "execution",
    "failure",
    "recovery",
    "strategy",
    "learning",
]
OperationalMemoryStatus = Literal["observed", "active", "superseded", "archived"]
OperationalMemoryConfidence = Literal["low", "medium", "high", "confirmed"]


class OperationalMemoryEvidence(AIpinhoModel):
    evidence_type: str
    ref_id: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalMemoryRecord(AIpinhoModel):
    memory_id: str = Field(default_factory=lambda: f"operational_memory_{uuid4().hex}")
    memory_type: OperationalMemoryType
    title: str
    summary: str
    status: OperationalMemoryStatus = "observed"
    confidence: OperationalMemoryConfidence = "medium"
    source_type: str = "task_run"
    source_run_id: str | None = None
    source_node_id: str | None = None
    source_step_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    operation_type: str | None = None
    contract_type: str | None = None
    runtime_profile: str | None = None
    outcome: str | None = None
    reusable_when: list[str] = Field(default_factory=list)
    avoid_when: list[str] = Field(default_factory=list)
    evidence: list[OperationalMemoryEvidence] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class DecisionMemory(OperationalMemoryRecord):
    memory_type: Literal["decision"] = "decision"
    decision: str = "unknown"


class ExecutionMemory(OperationalMemoryRecord):
    memory_type: Literal["execution"] = "execution"
    executed_steps: list[str] = Field(default_factory=list)


class FailureMemory(OperationalMemoryRecord):
    memory_type: Literal["failure"] = "failure"
    failure_code: str = "unknown"


class RecoveryMemory(OperationalMemoryRecord):
    memory_type: Literal["recovery"] = "recovery"
    recovery_action: str = "unknown"


class StrategyMemory(OperationalMemoryRecord):
    memory_type: Literal["strategy"] = "strategy"
    strategy: str = "unknown"


class LearningMemory(OperationalMemoryRecord):
    memory_type: Literal["learning"] = "learning"
    lesson: str = "unknown"


class OperationalMemorySnapshot(AIpinhoModel):
    run_id: str
    records: list[OperationalMemoryRecord] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
