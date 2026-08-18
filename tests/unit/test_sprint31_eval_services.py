from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals.citation_coverage_evaluator import CitationCoverageEvaluator
from aipinho.services.evals.fallback_analysis_service import FallbackAnalysisService
from aipinho.services.evals.grounding_evaluator import GroundingEvaluator
from aipinho.services.evals.hallucination_signal_evaluator import HallucinationSignalEvaluator
from aipinho.services.evals.latency_cost_evaluator import LatencyCostEvaluator


def test_citation_coverage_fails_without_required_citations():
    result = CitationCoverageEvaluator().evaluate(
        EvalRequest(payload={"contextual_claims": 2, "available_citation_ids": ["src_1"], "output_citation_ids": []})
    )

    assert result.status == "failed"
    assert result.findings[0].code == "missing_context_citations"


def test_grounding_flags_claims_outside_allowed_refs():
    result = GroundingEvaluator().evaluate(
        EvalRequest(payload={"output": "Patch applied", "allowed_refs": ["src_1"], "referenced_refs": ["src_2"]})
    )

    assert result.status == "failed"
    assert {finding.code for finding in result.findings} >= {"unsupported_source_reference", "unsupported_execution_claim"}


def test_hallucination_signals_require_trace_and_results():
    result = HallucinationSignalEvaluator().evaluate(
        EvalRequest(
            payload={
                "claims_patch_applied": True,
                "claims_tests_run": True,
                "claims_rag_used": True,
                "claims_vision_ocr_used": True,
                "model_id": "qwen2_5_coder_14b",
                "manual_escalation_used": False,
            }
        )
    )

    assert result.status == "failed"
    codes = {finding.code for finding in result.findings}
    assert "patch_applied_without_result" in codes
    assert "tests_run_without_result" in codes
    assert "rag_used_without_trace" in codes
    assert "vision_ocr_used_without_trace" in codes
    assert "auto_selected_14b" in codes


def test_latency_and_fallback_checks_are_policy_style_evals():
    latency = LatencyCostEvaluator().evaluate(EvalRequest(payload={"model_id": "14b", "latency_warning_acknowledged": False}))
    fallback = FallbackAnalysisService().evaluate(EvalRequest(payload={"fallback_used": True, "fallback_model_id": "14b"}))

    assert latency.status == "failed"
    assert fallback.status == "failed"
    assert any(finding.code == "manual_14b_latency_ack_missing" for finding in latency.findings)
    assert any(finding.code == "fallback_reason_missing" for finding in fallback.findings)
    assert any(finding.code == "fallback_to_14b_critical" for finding in fallback.findings)
