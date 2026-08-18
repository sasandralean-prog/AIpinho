from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals.hallucination_signal_evaluator import HallucinationSignalEvaluator


class ModelBenchmarkRunner(HallucinationSignalEvaluator):
    evaluator = "model"
