from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.context.contracts import ContextInjectionPlan
from aipinho.services.context.context_core import ContextBundleRepository
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ContextPlanResolution:
    status: str
    source: str | None = None
    plan: dict[str, Any] = field(default_factory=dict)
    bundle: dict[str, Any] = field(default_factory=dict)
    evidence_context: list[dict[str, Any]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CanonicalContextPlanStore:
    """Persistence only. ContextKernel remains the context/admission authority."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "context" / "plans"

    def save(self, plan: ContextInjectionPlan) -> ContextInjectionPlan:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{plan.plan_id}.json"
        path.write_text(
            json.dumps(plan.model_dump(mode="json"), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return plan

    def get(self, plan_id: str) -> ContextInjectionPlan | None:
        path = self.root / f"{plan_id}.json"
        if not path.exists():
            return None
        return ContextInjectionPlan.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )


class ContextPlanRuntimeService:
    """Single TaskRuntime-facing resolver for canonical context plans.

    Generic ContextKernel plans are authoritative for new runtime handoffs.
    The legacy RAG planner is read only through an explicitly configured
    compatibility adapter while its callers are migrated.
    """

    def __init__(
        self,
        *,
        store: CanonicalContextPlanStore | None = None,
        bundles: ContextBundleRepository | None = None,
        legacy_planner: ContextInjectionPlanner | None = None,
        legacy_validator: ContextUsageValidator | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.store = store or CanonicalContextPlanStore()
        self.bundles = bundles or ContextBundleRepository()
        self.legacy_planner = legacy_planner or ContextInjectionPlanner()
        self.legacy_validator = legacy_validator or ContextUsageValidator()
        self.config_path = (
            config_path
            or PATHS.config_root / "context" / "runtime_context_handoff_policy.yaml"
        )
        self.config = load_yaml_file(
            self.config_path,
            critical=True,
            root=self.config_path.parent,
        )

    def persist(self, plan: ContextInjectionPlan) -> ContextInjectionPlan:
        return self.store.save(plan)

    def resolve(self, plan_id: str | None) -> ContextPlanResolution:
        if not plan_id:
            return ContextPlanResolution(status="not_applicable")

        plan = self.store.get(plan_id)
        if plan is not None:
            return self._resolve_canonical(plan)

        compatibility = (
            self.config.get("compatibility", {})
            if isinstance(self.config.get("compatibility"), dict)
            else {}
        )
        if not bool(compatibility.get("allow_legacy_rag_plan_resolution", False)):
            return ContextPlanResolution(
                status="blocked",
                violations=["context_injection_plan_not_found"],
            )

        legacy = self.legacy_planner.get_plan(plan_id)
        if legacy is None:
            return ContextPlanResolution(
                status="blocked",
                violations=["context_injection_plan_not_found"],
            )
        validation = self.legacy_validator.validate_plan(legacy)
        evidence_context = [
            {
                "evidence_id": item.context_item_id,
                "artifact_id": (
                    item.source_id if item.kind in {"evidence_item", "report_section"} else ""
                ),
                "logical_path": str(
                    (item.metadata or {}).get("logical_path")
                    or (item.metadata or {}).get("source_path")
                    or item.source_id
                ),
                "content": item.content,
                "citation_ids": list(item.citation_ids),
                "source_type": item.source_type,
            }
            for item in legacy.context_items
        ]
        return ContextPlanResolution(
            status="ready" if validation.valid else "blocked",
            source="legacy_rag_adapter",
            plan=legacy.model_dump(mode="json"),
            evidence_context=evidence_context,
            violations=list(validation.violations),
            warnings=[
                *list(validation.warnings),
                "legacy_rag_context_plan_adapter",
            ],
        )

    def _resolve_canonical(
        self,
        plan: ContextInjectionPlan,
    ) -> ContextPlanResolution:
        violations: list[str] = []
        warnings = [warning.code for warning in plan.warnings]
        bundle = self.bundles.get(plan.bundle_id)
        if bundle is None:
            violations.append("context_bundle_not_found")
            return ContextPlanResolution(
                status="blocked",
                source="context_kernel",
                plan=plan.model_dump(mode="json"),
                violations=violations,
                warnings=warnings,
            )
        if not plan.safe_for_prompt_assembly or not bundle.safe_for_prompt:
            violations.append("unsafe_context_injection_plan")
        if plan.purpose != bundle.purpose:
            violations.append("context_plan_purpose_mismatch")

        evidence_context: list[dict[str, Any]] = []
        for item in bundle.items:
            evidence_context.append(
                {
                    "evidence_id": (
                        item.evidence_refs[0].evidence_id
                        if item.evidence_refs
                        else item.item_id
                    ),
                    "artifact_id": (
                        item.source_ref.source_id
                        if item.source_type in {"artifact_record", "artifact_manifest"}
                        else ""
                    ),
                    "logical_path": (
                        item.source_ref.path
                        or item.source_ref.source_id
                    ),
                    "content": item.content,
                    "citation_ids": [
                        citation.citation_id for citation in item.citations
                    ],
                    "source_type": item.source_type,
                }
            )
        return ContextPlanResolution(
            status="ready" if not violations else "blocked",
            source="context_kernel",
            plan=plan.model_dump(mode="json"),
            bundle=bundle.model_dump(mode="json"),
            evidence_context=evidence_context,
            violations=violations,
            warnings=warnings,
        )

    def status(self) -> dict[str, object]:
        compatibility = (
            self.config.get("compatibility", {})
            if isinstance(self.config.get("compatibility"), dict)
            else {}
        )
        return {
            "status": "ok",
            "service": "context_plan_runtime",
            "canonical_owner": "context_kernel",
            "legacy_rag_adapter_enabled": bool(
                compatibility.get("allow_legacy_rag_plan_resolution", False)
            ),
        }
