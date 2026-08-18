from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest, EvalStatusModel
from aipinho.services.evals.citation_coverage_evaluator import CitationCoverageEvaluator
from aipinho.services.evals.end_to_end_eval_service import EndToEndEvalService
from aipinho.services.evals.fallback_analysis_service import FallbackAnalysisService
from aipinho.services.evals.grounding_evaluator import GroundingEvaluator
from aipinho.services.evals.hallucination_signal_evaluator import HallucinationSignalEvaluator
from aipinho.services.evals.latency_cost_evaluator import LatencyCostEvaluator
from aipinho.services.evals.model_benchmark_runner import ModelBenchmarkRunner
from aipinho.services.evals.rag_evaluation_service import RAGEvaluationService
from aipinho.services.evals.role_benchmark_runner import RoleBenchmarkRunner
from aipinho.services.evals.vision_ocr_evaluator import VisionOCREvaluator


class EvaluationWorkbenchService:
    EVALUATORS = {
        "model": ModelBenchmarkRunner,
        "role": RoleBenchmarkRunner,
        "rag": RAGEvaluationService,
        "citation_coverage": CitationCoverageEvaluator,
        "context_grounding": GroundingEvaluator,
        "hallucination_signals": HallucinationSignalEvaluator,
        "latency_cost": LatencyCostEvaluator,
        "fallback_analysis": FallbackAnalysisService,
        "vision_ocr": VisionOCREvaluator,
        "end_to_end": EndToEndEvalService,
    }

    def status_model(self) -> EvalStatusModel:
        return EvalStatusModel(evaluators=list(self.EVALUATORS))

    def status(self) -> dict[str, object]:
        return {"status": "ok", **self.status_model().model_dump()}

    def evaluate(self, evaluator: str, request: EvalRequest):
        cls = self.EVALUATORS[evaluator]
        return cls().evaluate(request)
