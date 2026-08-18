from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.evaluation.evaluation_result import EvaluationResult
from aipinho.services.evaluation.evidence_requirement_validator import EvidenceRequirementValidator
from aipinho.services.evaluation.fallback_policy_service import FallbackPolicyService
from aipinho.services.evaluation.hallucination_signal_detector import HallucinationSignalDetector
from aipinho.services.evaluation.model_response_evaluator import ModelResponseEvaluator
from aipinho.services.evaluation.output_contract_validator import OutputContractValidator
from aipinho.services.evaluation.refusal_compliance_checker import RefusalComplianceChecker
from aipinho.services.evaluation.retry_policy_service import RetryPolicyService
from aipinho.services.evaluation.safety_envelope_validator import SafetyEnvelopeValidator
from aipinho.services.evaluation.truncation_detector import TruncationDetector

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


class OutputContractValidationRequest(BaseModel):
    content: str = ""
    output_contract: dict[str, Any] = Field(default_factory=dict)


class SafetyValidationRequest(BaseModel):
    content: str = ""
    safety_envelope: dict[str, Any] = Field(default_factory=dict)
    policy_decision: dict[str, Any] = Field(default_factory=dict)


class EvidenceValidationRequest(BaseModel):
    content: str = ""
    evidence_context: list[dict[str, Any]] = Field(default_factory=list)
    output_contract: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
def get_evaluation_status() -> dict[str, object]:
    evaluator = ModelResponseEvaluator()
    return {
        "status": "ok",
        "evaluation": evaluator.status(),
        "output_contract_validation": OutputContractValidator().status(),
        "safety_validation": SafetyEnvelopeValidator().status(),
        "evidence_validation": EvidenceRequirementValidator().status(),
        "hallucination_signals": HallucinationSignalDetector().status(),
        "truncation": TruncationDetector().status(),
        "retry_policy": RetryPolicyService().status(),
        "refusal_compliance": RefusalComplianceChecker().status(),
        "fallback_policy": FallbackPolicyService().status(),
        "tool_calling_enabled_from_model": False,
        "write_enabled": False,
        "patch_enabled": False,
        "shell_enabled": False,
        "rag_enabled": False,
        "memory_write_enabled": False,
    }


@router.post("/model-response")
def evaluate_model_response(request: EvaluationRequest) -> dict[str, object]:
    result = ModelResponseEvaluator().evaluate(request)
    return result.model_dump()


@router.post("/output-contract")
def validate_output_contract(request: OutputContractValidationRequest) -> dict[str, object]:
    return OutputContractValidator().validate(request.content, request.output_contract).model_dump()


@router.post("/safety")
def validate_safety(request: SafetyValidationRequest) -> dict[str, object]:
    return SafetyEnvelopeValidator().validate(request.content, request.safety_envelope, request.policy_decision)


@router.post("/evidence")
def validate_evidence(request: EvidenceValidationRequest) -> dict[str, object]:
    return EvidenceRequirementValidator().validate(request.content, request.output_contract, request.evidence_context).model_dump()


@router.post("/retry-decision")
def retry_decision(request: EvaluationResult) -> dict[str, object]:
    return RetryPolicyService().decide(request.violations, truncation_detected=request.truncation_detected).model_dump()

