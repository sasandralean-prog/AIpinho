from __future__ import annotations
from aipinho.core.paths import PATHS
from aipinho.schemas.validation.validation_finding import ValidationFinding
from aipinho.schemas.validation.validation_score import ValidationScore
from aipinho.utils.yaml_loader import load_yaml_file

class ValidationScoreService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "validation" / "quality_score_policy.yaml", critical=True, root=PATHS.config_root / "validation")

    def score(self, findings: list[ValidationFinding], *, validator_error: bool = False) -> ValidationScore:
        score_policy = self.policy.get("score", {}) if isinstance(self.policy.get("score", {}), dict) else {}
        penalties = self.policy.get("penalties", {}) if isinstance(self.policy.get("penalties", {}), dict) else {}
        value = float(score_policy.get("start", 1.0))
        applied: list[str] = []
        overrides: list[str] = []
        seen_penalties: set[str] = set()
        if validator_error:
            return ValidationScore(score=0.0, status="degraded", penalties_applied=["validator_error"], critical_overrides=["validator_error"])
        for item in findings:
            penalty_key = self._penalty_key(item.code)
            penalty = float(penalties.get(penalty_key, 0.10 if item.severity in {"warning", "error"} else 0.0))
            if item.severity == "critical":
                penalty = max(penalty, 0.50)
            if penalty and penalty_key not in seen_penalties:
                value -= penalty
                applied.append(penalty_key)
                seen_penalties.add(penalty_key)
            if item.code in {"side_effect_violation", "forbidden_root_access", "secret_leak", "patch_detected", "shell_detected", "policy_denied_target", "real_inference_auto_use"}:
                overrides.append(item.code)
        value = max(0.0, min(1.0, value))
        if overrides:
            status = "rejected" if "secret_leak" in overrides else "failed"
        elif any(item.code in {"missing_evidence", "empty_output"} and item.blocking for item in findings):
            status = "rejected"
        elif any(item.blocking and item.severity == "error" for item in findings):
            status = "failed"
        elif any(item.severity == "critical" for item in findings):
            status = "failed"
        elif value >= float(score_policy.get("minimum_pass", 0.8)) and not findings:
            status = "passed"
        elif value >= float(score_policy.get("minimum_pass_with_warnings", 0.65)):
            status = "passed_with_warnings" if findings else "passed"
        elif value >= float(score_policy.get("minimum_needs_review", 0.45)):
            status = "needs_review"
        else:
            status = "failed"
        return ValidationScore(score=round(value, 4), status=status, penalties_applied=list(dict.fromkeys(applied)), critical_overrides=list(dict.fromkeys(overrides)))

    def _penalty_key(self, code: str) -> str:
        mapping = {
            "missing_required_section": "missing_required_section",
            "missing_evidence": "missing_evidence",
            "invalid_evidence": "invalid_evidence",
            "missing_limitations_when_partial": "missing_limitations_when_partial",
            "status_inconsistency": "status_inconsistency",
            "side_effect_violation": "side_effect_signal",
            "forbidden_root_access": "forbidden_root_signal",
            "secret_leak": "secret_leak",
            "unsupported_claim": "unsupported_claim",
            "empty_output": "empty_output",
            "weak_evidence": "invalid_evidence",
            "event_order_invalid": "status_inconsistency",
            "duplicate_execution_signal": "status_inconsistency",
        }
        return mapping.get(code, code)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "validation_score", "deterministic_only": True}
