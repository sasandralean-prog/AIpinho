from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aipinho.schemas.rag.integration.contracts import ContextAdmissionRequest, ContextInjectionPlan, RAGMemoryPolicyDecision, RAGMemoryPolicyRequest
from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_audit_service import ContextUsageAuditService
from aipinho.services.rag.integration.rag_memory_policy_service import RAGMemoryPolicyService


def cited_retrieval(
    *,
    text: str = "Validation gate is enabled.",
    citation_id: str = "citation_report_01",
    source_ref: str = "reports/status.md",
    status: str = "found",
) -> tuple[dict, dict]:
    citation = {
        "citation_id": citation_id,
        "citation_type": "report_section",
        "source_ref": {
            "source_id": "project_reports",
            "source_type": "project_report",
            "ref": source_ref,
            "location": f"{source_ref}:validation",
            "content_hash": "a" * 64,
        },
        "excerpt": text,
    }
    hit = {
        "source_id": "project_reports",
        "source_type": "project_report",
        "excerpt": text,
        "score": 0.9,
        "citation": citation,
        "metadata": {"quality_status": "passed"},
    }
    bundle = {
        "bundle_id": "retrieval_bundle_test",
        "retrieval_id": "retrieval_test",
        "status": status,
        "hits": [hit],
        "citations": [citation],
        "source_refs": [citation["source_ref"]],
        "scope": {"scope_type": "project", "source_ids": ["project_reports"]},
        "safe_for_prompt_assembly": True,
        "warnings": ["partial_source"] if status == "partial" else [],
    }
    result = {
        "retrieval_id": "retrieval_test",
        "status": status,
        "sources_requested": ["project_reports"],
        "sources_used": ["project_reports"],
        "hits": [hit],
        "context_bundle": bundle,
        "warnings": bundle["warnings"],
    }
    return result, bundle


def memory(
    *,
    memory_id: str = "memory_test",
    status: str = "active",
    text: str = "Patch apply requires approval.",
    workspace: str | None = None,
    age_days: int = 0,
) -> dict:
    created = datetime.now(timezone.utc) - timedelta(days=age_days)
    return {
        "memory_id": memory_id,
        "status": status,
        "kind": "engineering_rule",
        "summary": text,
        "text": text,
        "scope": {"scope_type": "project", "workspace": workspace},
        "evidence": [{"evidence_id": "evidence_01", "summary": "Approved source evidence."}],
        "version": 1,
        "created_at": created.isoformat(),
        "updated_at": created.isoformat(),
    }


def explicit_policy(*, sources: list[str] | None = None, workspace: str | None = None) -> RAGMemoryPolicyDecision:
    requested = sources or ["project_reports"]
    return RAGMemoryPolicyService().decide(
        RAGMemoryPolicyRequest(
            usage_mode="explicit_user_request",
            intent_type="readonly_analysis",
            workspace=workspace,
            requested_sources=requested,
            allow_retrieval=any(source != "curated_memory" for source in requested),
            allow_curated_memory="curated_memory" in requested,
            scope={"workspace": workspace} if workspace else {},
            user_request="Use governed context.",
            include_trace=True,
        )
    )


def admitted_retrieval(*, text: str = "Validation gate is enabled.", budget: dict | None = None):
    result, bundle = cited_retrieval(text=text)
    return ContextAdmissionService().admit(
        ContextAdmissionRequest(
            policy_decision=explicit_policy(),
            retrieval_result=result,
            retrieval_context_bundle=bundle,
            budget=budget or {},
            usage_mode="explicit_user_request",
            include_trace=True,
        )
    )


def ready_plan(tmp_path, *, text: str = "Validation gate is enabled.") -> ContextInjectionPlan:
    planner = ContextInjectionPlanner(audit=ContextUsageAuditService(root=tmp_path / "context_plans"))
    return planner.plan(admitted_retrieval(text=text), policy_decision_id="decision_test")
