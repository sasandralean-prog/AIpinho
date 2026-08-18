from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding

class ReportSectionValidator:
    def validate(self, report: Any) -> list:
        data = as_dict(report)
        findings = []
        if not str(data.get("executive_summary") or "").strip():
            findings.append(finding("missing_required_section", "Missing executive summary", "ProjectReport requires an executive_summary.", severity="error", validator="report_section", blocking=True))
        if data.get("findings") is None:
            findings.append(finding("missing_required_section", "Missing findings section", "ProjectReport requires findings field.", severity="error", validator="report_section", blocking=True))
        if data.get("recommendations") is None:
            findings.append(finding("missing_required_section", "Missing recommendations section", "ProjectReport requires recommendations field.", severity="error", validator="report_section", blocking=True))
        if data.get("limitations") is None:
            findings.append(finding("missing_required_section", "Missing limitations section", "ProjectReport requires limitations field.", severity="error", validator="report_section", blocking=True))
        return findings

    def status(self): return {"status": "ok", "service": "report_section_validator"}
