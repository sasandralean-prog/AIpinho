from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding
from aipinho.services.validation.source_citation_validator import SourceCitationValidator

class EvidenceComplianceValidator:
    def __init__(self) -> None:
        self.citation = SourceCitationValidator()

    def validate(self, payload: Any) -> list:
        data = as_dict(payload)
        findings = []
        report = data.get("report", data)
        evidence_index = report.get("evidence_index") or report.get("evidence") or data.get("evidence") or []
        valid_ids = {item.get("evidence_id") for item in evidence_index if isinstance(item, dict)}
        for citation in evidence_index:
            findings.extend(self.citation.validate_evidence(citation))
        for item in report.get("findings", []) or []:
            if not isinstance(item, dict):
                continue
            ev = item.get("evidence") or []
            if not ev:
                findings.append(finding("missing_evidence", "Finding without evidence", f"Finding {item.get('finding_id') or item.get('title')} has no evidence.", severity="critical", validator="evidence_compliance", blocking=True))
                continue
            if item.get("severity") in {"high", "critical"} and len(ev) < (2 if item.get("severity") == "critical" else 1):
                findings.append(finding("weak_evidence", "Weak evidence", "High/critical finding requires stronger evidence.", severity="error", validator="evidence_compliance", evidence=[str(item.get("finding_id"))], blocking=item.get("severity") == "critical"))
            for citation in ev:
                citation_id = citation.get("evidence_id") if isinstance(citation, dict) else None
                if citation_id and valid_ids and citation_id not in valid_ids and not self._is_inline_citation(citation):
                    findings.append(finding("invalid_evidence", "Invalid evidence id", f"Evidence id {citation_id} is not present in evidence index.", severity="error", validator="evidence_compliance", evidence=[str(citation_id)], blocking=True))
                findings.extend(self.citation.validate_evidence(citation))
        return findings

    def _is_inline_citation(self, citation: Any) -> bool:
        data = as_dict(citation)
        return bool(data.get("source_type") == "absence" and data.get("path") and data.get("excerpt"))

    def status(self): return {"status": "ok", "service": "evidence_compliance_validator"}
