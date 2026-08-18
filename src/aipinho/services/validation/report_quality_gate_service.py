from __future__ import annotations
from typing import Any
from aipinho.services.validation.gate_decision_service import GateDecisionService
from aipinho.services.validation.validation_store import ValidationStore
from aipinho.services.validation.validation_trace_service import ValidationTraceService

class ReportQualityGateService:
    def __init__(self, store: ValidationStore | None = None) -> None:
        from aipinho.services.validation.evidence_compliance_validator import EvidenceComplianceValidator
        from aipinho.services.validation.finding_quality_validator import FindingQualityValidator
        from aipinho.services.validation.limitation_honesty_validator import LimitationHonestyValidator
        from aipinho.services.validation.recommendation_quality_validator import RecommendationQualityValidator
        from aipinho.services.validation.report_section_validator import ReportSectionValidator
        from aipinho.services.validation.side_effect_validator import SideEffectValidator
        self.sections = ReportSectionValidator()
        self.findings = FindingQualityValidator()
        self.recommendations = RecommendationQualityValidator()
        self.limitations = LimitationHonestyValidator()
        self.evidence = EvidenceComplianceValidator()
        self.side_effects = SideEffectValidator()
        self.decision = GateDecisionService()
        self.store = store or ValidationStore()
        self.trace = ValidationTraceService()

    def collect_findings(self, report: Any) -> list:
        from aipinho.services.validation.validation_common import as_dict, contains_secret, finding
        data = as_dict(report)
        findings = []
        if not data or not any([data.get("executive_summary"), data.get("findings"), data.get("sections")]):
            findings.append(finding("empty_output", "Empty report", "Report has no useful content.", severity="critical", validator="report_quality", blocking=True))
            return findings
        if contains_secret(data):
            findings.append(finding("secret_leak", "Secret-like report content", "Report contains secret-like material.", severity="critical", validator="report_quality", blocking=True))
        findings.extend(self.sections.validate(data))
        findings.extend(self.limitations.validate(data))
        findings.extend(self.recommendations.validate(data))
        findings.extend(self.evidence.validate({"report": data}))
        findings.extend(self.side_effects.validate(data))
        for item in data.get("findings", []) or []:
            findings.extend(self.findings.validate(item))
        return findings

    def validate_report(self, report: Any, *, target_id: str | None = None):
        data = report.model_dump() if hasattr(report, "model_dump") else report
        findings = self.collect_findings(data)
        trace = [self.trace.item("report_quality_gate", "checked", "report_quality_rules_applied", source="config/validation/report_quality_gate_policy.yaml", data={"findings": len(findings)})]
        result = self.decision.build_result(target_type="project_report", target_id=target_id or (data.get("report_id") if isinstance(data, dict) else None), findings=findings, trace=trace, metadata={"report_quality_gate": True})
        return self.store.save_result(result)

    def status(self): return {"status": "ok", "service": "report_quality_gate", "deterministic_only": True}
