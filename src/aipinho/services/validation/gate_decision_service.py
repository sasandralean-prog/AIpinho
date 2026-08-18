from __future__ import annotations
from uuid import uuid4
from aipinho.schemas.validation.validation_gate_result import ValidationGateResult
from aipinho.schemas.validation.validation_finding import ValidationFinding
from aipinho.schemas.validation.validation_trace import ValidationTraceItem
from aipinho.services.validation.validation_score_service import ValidationScoreService

class GateDecisionService:
    def __init__(self, scorer: ValidationScoreService | None = None) -> None:
        self.scorer = scorer or ValidationScoreService()

    def build_result(self, *, target_type: str, target_id: str | None, findings: list[ValidationFinding], warnings: list[str] | None = None, trace: list[ValidationTraceItem] | None = None, metadata: dict | None = None, validator_error: bool = False) -> ValidationGateResult:
        score = self.scorer.score(findings, validator_error=validator_error)
        blocking = [item.code for item in findings if item.blocking or item.severity in {"error", "critical"}]
        safe = score.status not in {"rejected"} and not any(code in {"secret_leak"} for code in blocking)
        return ValidationGateResult(validation_id=f"validation_{uuid4().hex}", target_type=target_type, target_id=target_id, status=score.status, score=score.score, safe_to_display=safe, findings=findings, warnings=list(dict.fromkeys(warnings or [])), blocking_findings=list(dict.fromkeys(blocking)), trace=list(trace or []), metadata=metadata or {})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "gate_decision", "deterministic_only": True}
