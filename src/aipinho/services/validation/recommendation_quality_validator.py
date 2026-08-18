from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, finding

class RecommendationQualityValidator:
    def validate(self, report: Any) -> list:
        data = as_dict(report)
        findings = []
        for item in data.get("recommendations", []) or []:
            rec = as_dict(item)
            text = " ".join(str(value) for value in rec.values()).lower()
            if any(term in text for term in ["aplicar patch", "apply patch", "git push", "execute comando", "run command"]):
                findings.append(finding("unsafe_recommendation", "Unsafe recommendation", "Recommendation suggests side effect without approval flow.", severity="warning", validator="recommendation_quality", evidence=[text[:120]]))
        return findings

    def status(self): return {"status": "ok", "service": "recommendation_quality_validator"}
