from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding

class LimitationHonestyValidator:
    def validate(self, report: Any) -> list:
        data = as_dict(report)
        findings = []
        status = str(data.get("status") or "")
        limitations = list(data.get("limitations") or [])
        warnings = list(data.get("warnings") or [])
        if status in {"partial", "degraded"} and not limitations:
            findings.append(finding("missing_limitations_when_partial", "Partial/degraded report without limitations", "Partial or degraded reports must describe limitations.", severity="error", validator="limitation_honesty", blocking=True))
        signal_text = " ".join([*limitations, *warnings]).lower()
        if any(term in signal_text for term in ["budget", "omitted", "blocked", "limit"]) and not limitations:
            findings.append(finding("missing_limitations_when_partial", "Missing limitations for budget/blocked context", "Budget or blocked-file signal requires limitations.", severity="error", validator="limitation_honesty", blocking=True))
        if status in {"partial", "degraded"} and "com certeza" in str(data.get("executive_summary", "")).lower():
            findings.append(finding("unsupported_claim", "Overconfident partial report", "Partial report uses absolute certainty wording.", severity="warning", validator="limitation_honesty"))
        return findings

    def status(self): return {"status": "ok", "service": "limitation_honesty_validator"}
