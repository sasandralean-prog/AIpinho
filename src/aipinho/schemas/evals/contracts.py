from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

EvalStatus = Literal["passed", "passed_with_warnings", "failed", "degraded", "blocked"]
FindingSeverity = Literal["info", "warning", "high", "critical"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EvalTrace(AIpinhoModel):
    trace_id: str = Field(default_factory=lambda: f"eval_trace_{uuid4().hex}")
    events: list[dict[str, Any]] = Field(default_factory=list)


class EvalFinding(AIpinhoModel):
    finding_id: str = Field(default_factory=lambda: f"eval_finding_{uuid4().hex}")
    severity: FindingSeverity = "warning"
    code: str
    message: str
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class EvalRequest(AIpinhoModel):
    target_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    include_trace: bool = True


class EvalResult(AIpinhoModel):
    eval_run_id: str = Field(default_factory=lambda: f"eval_run_{uuid4().hex}")
    status: EvalStatus
    score: float = 1.0
    evaluator: str
    findings: list[EvalFinding] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    trace: EvalTrace | None = None
    read_only: bool = True
    created_at: str = Field(default_factory=utc_now)


class EvalRun(AIpinhoModel):
    request: EvalRequest
    result: EvalResult


class ModelEvalRequest(EvalRequest):
    pass


class ModelEvalResult(EvalResult):
    evaluator: str = "model"


class RoleEvalRequest(EvalRequest):
    pass


class RoleEvalResult(EvalResult):
    evaluator: str = "role"


class RAGEvalRequest(EvalRequest):
    pass


class RAGEvalResult(EvalResult):
    evaluator: str = "rag"


class CitationCoverageEval(EvalResult):
    evaluator: str = "citation_coverage"


class GroundingEval(EvalResult):
    evaluator: str = "grounding"


class HallucinationSignalEval(EvalResult):
    evaluator: str = "hallucination_signals"


class LatencyCostEval(EvalResult):
    evaluator: str = "latency_cost"


class FallbackAnalysisResult(EvalResult):
    evaluator: str = "fallback_analysis"


class VisionOCREvalResult(EvalResult):
    evaluator: str = "vision_ocr"


class EndToEndEvalResult(EvalResult):
    evaluator: str = "end_to_end"


class EvalReport(AIpinhoModel):
    report_id: str = Field(default_factory=lambda: f"eval_report_{uuid4().hex}")
    status: EvalStatus = "passed"
    results: list[EvalResult] = Field(default_factory=list)
    summary: str = ""


class EvalStatusModel(AIpinhoModel):
    enabled: bool = True
    mode: str = "read_only_evaluation"
    workspace_write_enabled: bool = False
    patch_apply_enabled: bool = False
    shell_enabled: bool = False
    git_enabled: bool = False
    memory_mutation_enabled: bool = False
    rag_ingestion_execute_enabled: bool = False
    evaluators: list[str] = Field(default_factory=list)
