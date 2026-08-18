from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.evaluation.evaluation_request import EvaluationRequest
from aipinho.schemas.evaluation.evaluation_result import EvaluationResult
from aipinho.schemas.rag.integration.contracts import ContextInjectionPlan
from aipinho.services.evaluation.evaluation_audit_service import EvaluationAuditService
from aipinho.services.evaluation.evaluation_trace_service import EvaluationTraceService
from aipinho.services.evaluation.evidence_requirement_validator import EvidenceRequirementValidator
from aipinho.services.evaluation.fallback_policy_service import FallbackPolicyService
from aipinho.services.evaluation.hallucination_signal_detector import HallucinationSignalDetector
from aipinho.services.evaluation.output_contract_validator import OutputContractValidator
from aipinho.services.evaluation.refusal_compliance_checker import RefusalComplianceChecker
from aipinho.services.evaluation.retry_policy_service import RetryPolicyService
from aipinho.services.evaluation.safety_envelope_validator import SafetyEnvelopeValidator
from aipinho.services.evaluation.truncation_detector import TruncationDetector
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.utils.yaml_loader import load_yaml_file


class ModelResponseEvaluator:
    def __init__(
        self,
        config_path: Path | None = None,
        config: dict[str, Any] | None = None,
        output_contract_validator: OutputContractValidator | None = None,
        safety_validator: SafetyEnvelopeValidator | None = None,
        evidence_validator: EvidenceRequirementValidator | None = None,
        hallucination_detector: HallucinationSignalDetector | None = None,
        truncation_detector: TruncationDetector | None = None,
        retry_policy: RetryPolicyService | None = None,
        fallback_policy: FallbackPolicyService | None = None,
        refusal_checker: RefusalComplianceChecker | None = None,
        trace_service: EvaluationTraceService | None = None,
        audit_service: EvaluationAuditService | None = None,
        context_usage_validator: ContextUsageValidator | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "model_response_evaluation_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.output_contract_validator = output_contract_validator or OutputContractValidator()
        self.safety_validator = safety_validator or SafetyEnvelopeValidator()
        self.evidence_validator = evidence_validator or EvidenceRequirementValidator()
        self.hallucination_detector = hallucination_detector or HallucinationSignalDetector()
        self.truncation_detector = truncation_detector or TruncationDetector()
        self.retry_policy = retry_policy or RetryPolicyService()
        self.fallback_policy = fallback_policy or FallbackPolicyService()
        self.refusal_checker = refusal_checker or RefusalComplianceChecker()
        self.trace_service = trace_service or EvaluationTraceService()
        self.audit_service = audit_service or EvaluationAuditService()
        self.context_usage_validator = context_usage_validator or ContextUsageValidator()

    def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        evaluation_cfg = self.config.get("evaluation", {}) if isinstance(self.config.get("evaluation", {}), dict) else {}
        scoring = self.config.get("scoring", {}) if isinstance(self.config.get("scoring", {}), dict) else {}
        content = str(request.model_response.get("content", ""))
        violations: list[str] = []
        warnings: list[str] = []
        trace = []
        score = float(scoring.get("start_score", 1.0) or 1.0)

        if evaluation_cfg.get("require_output_contract", True) and not request.output_contract:
            violations.append("output_contract_required")
            contract_result = self.output_contract_validator.validate(content, {"contract_type": "plain_text", "format": "text"})
            contract_result.valid = False
            contract_result.violations.append("output_contract_required")
        else:
            contract_result = self.output_contract_validator.validate(content, request.output_contract)
        violations.extend(contract_result.violations)
        warnings.extend(contract_result.warnings)
        if not contract_result.valid:
            score -= float(scoring.get("invalid_format_penalty", 0.4) or 0.4)
        trace.append(self.trace_service.item("output_contract", "ok" if contract_result.valid else "blocked", ",".join(contract_result.violations) or None, data=contract_result.model_dump()))

        if evaluation_cfg.get("require_safety_validation", True):
            safety_result = self.safety_validator.validate(content, request.safety_envelope, request.policy_decision)
        else:
            safety_result = {"valid": True, "violations": [], "warnings": []}
        safety_violations = [str(item.get("violation_id", item.get("type", "safety_violation"))) for item in safety_result.get("violations", [])]
        if safety_violations:
            violations.extend(safety_violations)
            violations.append("critical_safety_violation")
            score -= float(scoring.get("safety_violation_penalty", 0.6) or 0.6)
        warnings.extend([str(item) for item in safety_result.get("warnings", []) or []])
        trace.append(self.trace_service.item("safety_envelope", "ok" if safety_result.get("valid") else "blocked", ",".join(safety_violations) or None, data=safety_result))
        refusal_result = self.refusal_checker.check(content, request.model_response, request.policy_decision)
        violations.extend([str(item) for item in refusal_result.get("violations", []) or []])
        warnings.extend([str(item) for item in refusal_result.get("warnings", []) or []])
        trace.append(self.trace_service.item("refusal_compliance", "ok" if refusal_result.get("valid") else "blocked", ",".join(refusal_result.get("violations", []) or []) or None, data=refusal_result))

        contract_requires_evidence = bool(request.output_contract.get("require_evidence") or request.output_contract.get("require_evidence_refs"))
        if evaluation_cfg.get("require_evidence_validation_when_contract_requires", True) and contract_requires_evidence:
            evidence_result = self.evidence_validator.validate(content, request.output_contract, request.evidence_context)
        else:
            evidence_result = self.evidence_validator.validate(content, request.output_contract, request.evidence_context)
            if not contract_requires_evidence:
                evidence_result.valid = True if not evidence_result.unseen_file_refs else True
                evidence_result.violations = []
        violations.extend(evidence_result.violations)
        warnings.extend(evidence_result.warnings)
        if evidence_result.violations:
            score -= float(scoring.get("missing_evidence_penalty", 0.5) or 0.5)
        trace.append(self.trace_service.item("evidence", "ok" if evidence_result.valid else "blocked", ",".join(evidence_result.violations) or None, data=evidence_result.model_dump()))

        context_usage_valid = True
        if request.context_injection_plan:
            try:
                context_plan = ContextInjectionPlan.model_validate(request.context_injection_plan)
                context_usage = self.context_usage_validator.validate_output(content, context_plan)
            except Exception:
                context_usage = None
                context_usage_valid = False
                violations.append("context_injection_plan_invalid")
                trace.append(self.trace_service.item("context_usage", "blocked", "context_injection_plan_invalid"))
            if context_usage is not None:
                context_usage_valid = context_usage.valid
                violations.extend(context_usage.violations)
                warnings.extend(context_usage.warnings)
                if not context_usage.valid:
                    score -= float(scoring.get("missing_evidence_penalty", 0.5) or 0.5)
                trace.append(
                    self.trace_service.item(
                        "context_usage",
                        "ok" if context_usage.valid else "blocked",
                        ",".join(context_usage.violations) or None,
                        data=context_usage.model_dump(),
                    )
                )

        hallucination_signals = self.hallucination_detector.detect(content, request.evidence_context, request.model_response.get("system_status", {}))
        if hallucination_signals:
            warnings.extend([item.code for item in hallucination_signals])
            score -= float(scoring.get("hallucination_signal_penalty", 0.3) or 0.3)
        trace.append(self.trace_service.item("hallucination_signals", "warning" if hallucination_signals else "ok", ",".join(item.code for item in hallucination_signals) or None, data={"signals": [item.model_dump() for item in hallucination_signals]}))

        truncation = self.truncation_detector.detect(content, request.model_response)
        truncation_detected = bool(truncation.get("truncation_detected"))
        if truncation_detected:
            warnings.extend([str(item) for item in truncation.get("reasons", []) or []])
            violations.extend(["invalid_json" if item == "incomplete_json" else "truncation" for item in truncation.get("reasons", []) or [] if item in {"incomplete_json", "finish_reason_length"}])
            score -= float(scoring.get("truncation_penalty", 0.2) or 0.2)
        trace.append(self.trace_service.item("truncation", "warning" if truncation_detected else "ok", ",".join(truncation.get("reasons", []) or []) or None, data=truncation))

        violations = list(dict.fromkeys(violations))
        warnings = list(dict.fromkeys(warnings))
        score = max(0.0, min(1.0, round(score, 3)))
        retry_decision = self.retry_policy.decide(violations, truncation_detected=truncation_detected)
        status = self._status(
            contract_valid=contract_result.valid,
            safety_valid=bool(safety_result.get("valid")),
            evidence_valid=evidence_result.valid and context_usage_valid,
            score=score,
            violations=violations,
            warnings=warnings,
            retry=retry_decision.should_retry,
        )
        fallback_decision = self.fallback_policy.decide(
            purpose=request.purpose,
            status=status,
            violations=violations,
            real_inference=bool(request.model_response.get("real_inference", False)),
        )
        result = EvaluationResult(
            evaluation_id=request.evaluation_id,
            status=status,
            score=score,
            contract_valid=contract_result.valid,
            safety_valid=bool(safety_result.get("valid")),
            evidence_valid=evidence_result.valid and context_usage_valid,
            format_valid=contract_result.format_valid,
            truncation_detected=truncation_detected,
            hallucination_signals=hallucination_signals,
            violations=violations,
            warnings=warnings,
            retry_decision=retry_decision,
            fallback_decision=fallback_decision,
            trace=trace if request.include_trace else [],
        )
        self.audit_service.record(result)
        return result

    def _status(self, *, contract_valid: bool, safety_valid: bool, evidence_valid: bool, score: float, violations: list[str], warnings: list[str], retry: bool) -> str:
        if "critical_safety_violation" in violations or "secret_leak" in violations or "policy_bypass" in violations:
            return "rejected"
        if retry:
            return "needs_retry"
        if not contract_valid or not evidence_valid:
            return "rejected"
        if not safety_valid:
            return "rejected"
        scoring = self.config.get("scoring", {}) if isinstance(self.config.get("scoring", {}), dict) else {}
        minimum_accept = float(scoring.get("minimum_accept_score", 0.7) or 0.7)
        minimum_warning = float(scoring.get("minimum_warning_score", 0.5) or 0.5)
        if score >= minimum_accept and not warnings:
            return "accepted"
        if score >= minimum_warning:
            return "accepted_with_warnings"
        return "degraded"

    def status(self) -> dict[str, object]:
        evaluation = self.config.get("evaluation", {}) if isinstance(self.config.get("evaluation", {}), dict) else {}
        integration = self.config.get("integration", {}) if isinstance(self.config.get("integration", {}), dict) else {}
        return {
            "status": "ok",
            "service": "model_response_evaluator",
            "enabled": bool(evaluation.get("enabled", True)),
            "evaluate_stub_responses": bool(integration.get("evaluate_stub_responses", True)),
            "evaluate_real_model_responses": bool(integration.get("evaluate_real_model_responses", True)),
            "chat_requires_evaluation": bool(integration.get("chat_requires_evaluation", False)),
            "reports_require_evaluation": bool(integration.get("reports_require_evaluation", True)),
            "context_usage_validation_enabled": True,
            "fabricated_context_citations_rejected": True,
        }



