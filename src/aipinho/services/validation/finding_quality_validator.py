from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, contains_secret, finding
from aipinho.services.validation.source_citation_validator import SourceCitationValidator

VALID_CATEGORIES = {"architecture", "policy", "routing", "schema", "service", "test", "security", "maintainability", "documentation", "risk", "limitations"}
VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}

class FindingQualityValidator:
    def __init__(self) -> None:
        self.citation = SourceCitationValidator()

    def validate(self, finding_value: Any) -> list:
        item = as_dict(finding_value)
        findings = []
        title = str(item.get("title") or "")
        if not title.strip():
            findings.append(finding("missing_finding_title", "Missing finding title", "Finding requires a title.", severity="error", validator="finding_quality", blocking=True))
        if item.get("category") not in VALID_CATEGORIES:
            findings.append(finding("missing_category", "Missing or invalid category", "Finding category is required and must be configured.", severity="error", validator="finding_quality", evidence=[str(item.get("category"))], blocking=True))
        if item.get("severity") not in VALID_SEVERITIES:
            findings.append(finding("missing_severity", "Missing or invalid severity", "Finding severity is required.", severity="error", validator="finding_quality", evidence=[str(item.get("severity"))], blocking=True))
        if item.get("confidence") is None:
            findings.append(finding("missing_confidence", "Missing confidence", "Finding confidence is required.", severity="warning", validator="finding_quality"))
        if not item.get("recommendation"):
            findings.append(finding("missing_recommendation", "Missing recommendation", "Finding requires a recommendation.", severity="warning", validator="finding_quality"))
        evidence = item.get("evidence") or []
        if not evidence:
            findings.append(finding("missing_evidence", "Finding without evidence", "Technical finding has no evidence and cannot pass the gate.", severity="critical", validator="finding_quality", evidence=[title], blocking=True))
        for ev in evidence:
            findings.extend(self.citation.validate_evidence(ev))
        if item.get("severity") == "critical" and len(evidence) < 2:
            findings.append(finding("weak_evidence", "Critical finding has weak evidence", "Critical finding requires at least two evidence citations.", severity="error", validator="finding_quality", evidence=[title], blocking=True))
        if contains_secret(item):
            findings.append(finding("secret_leak", "Secret-like content in finding", "Finding contains secret-like material.", severity="critical", validator="finding_quality", blocking=True))
        rec = str(item.get("recommendation") or "").lower()
        if any(term in rec for term in ["aplicar patch", "apply patch", "salve", "write file", "git push"]):
            findings.append(finding("unsafe_recommendation", "Unsafe recommendation", "Recommendation suggests write/patch/git without approval context.", severity="warning", validator="finding_quality", evidence=[rec[:120]]))
        return findings

    def status(self): return {"status": "ok", "service": "finding_quality_validator"}
