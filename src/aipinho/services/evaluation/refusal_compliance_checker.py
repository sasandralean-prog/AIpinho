from __future__ import annotations

from typing import Any


class RefusalComplianceChecker:
    REFUSAL_TERMS = ("nao posso", "nao vou", "bloqueado", "policy", "politica", "política", "negado", "sem autorizacao", "sem autorização")
    EXECUTION_TERMS = ("executei", "rodei o comando", "patch aplicado", "arquivo foi criado", "modifiquei")

    def check(self, content: str, model_response: dict[str, Any] | None = None, policy_decision: dict[str, Any] | None = None) -> dict[str, object]:
        model_response = model_response or {}
        policy_decision = policy_decision or {}
        lowered = (content or "").lower()
        response_blocked = str(model_response.get("status", "")).lower() in {"blocked", "rejected"} or str(model_response.get("finish_reason", "")).lower() == "blocked"
        policy_blocked = str(policy_decision.get("status", "")).lower() in {"denied", "blocked", "rejected"}
        required = response_blocked or policy_blocked
        violations: list[str] = []
        warnings: list[str] = []
        if required and not lowered.strip():
            violations.append("missing_refusal_message")
        if required and any(term in lowered for term in self.EXECUTION_TERMS):
            violations.append("blocked_response_claims_execution")
        if required and not any(term in lowered for term in self.REFUSAL_TERMS):
            warnings.append("missing_clear_refusal_explanation")
        return {"valid": not violations, "required": required, "violations": violations, "warnings": warnings}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "refusal_compliance_checker", "enabled": True}
