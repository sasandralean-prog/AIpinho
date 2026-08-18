from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.evaluation.evaluation_result import EvaluationResult


class ModelResponseEvaluation(AIpinhoModel):
    request: EvaluationRequest
    result: EvaluationResult
