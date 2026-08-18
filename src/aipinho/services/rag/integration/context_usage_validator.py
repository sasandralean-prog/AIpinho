from __future__ import annotations

import re

from aipinho.schemas.rag.integration.contracts import ContextInjectionPlan, ContextUsageValidation


class ContextUsageValidator:
    CITATION_PATTERN = re.compile(r"\b(?:citation_[A-Za-z0-9_]+)\b")
    PATH_PATTERN = re.compile(r"(?i)\b(?:src|tests|config|docs|reports)[\\/][A-Za-z0-9_.\\/-]+")

    def validate_plan(self, plan: ContextInjectionPlan) -> ContextUsageValidation:
        violations: list[str] = []
        if not plan.safe_for_prompt_assembly or plan.status not in {"ready", "partial"}:
            violations.append("unsafe_context_injection_plan")
        if not plan.citation_map.valid:
            violations.append("invalid_context_citation_map")
        if len(plan.citation_map.item_to_citations) != len(plan.context_items):
            violations.append("context_items_not_fully_mapped")
        return ContextUsageValidation(valid=not violations, status="accepted" if not violations else "rejected", violations=violations)

    def validate_output(self, content: str, plan: ContextInjectionPlan) -> ContextUsageValidation:
        base = self.validate_plan(plan)
        violations = list(base.violations)
        warnings: list[str] = []
        used = list(dict.fromkeys(self.CITATION_PATTERN.findall(content or "")))
        defined = set(plan.citation_map.citations)
        fabricated = [citation for citation in used if citation not in defined]
        if fabricated:
            violations.extend(f"fabricated_citation:{citation}" for citation in fabricated)
        if plan.context_items and content.strip() and not used:
            warnings.append("contextual_output_without_citation")
        allowed_refs = {
            str((citation.get("source_ref") or {}).get("ref") or "").replace("\\", "/").lower()
            for citation in plan.citation_map.citations.values()
        }
        for path in self.PATH_PATTERN.findall(content or ""):
            normalized = path.replace("\\", "/").lower()
            if normalized and not any(normalized == ref or normalized in ref for ref in allowed_refs):
                violations.append(f"unsupported_file_reference:{path}")
        violations = list(dict.fromkeys(violations))
        status = "rejected" if violations else ("accepted_with_warnings" if warnings else "accepted")
        return ContextUsageValidation(valid=not violations, status=status, used_citation_ids=used, warnings=warnings, violations=violations)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_usage_validator", "fabricated_citations_rejected": True}
