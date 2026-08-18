from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.utils.yaml_loader import load_yaml_file


class SeverityClassifier:
    ORDER = ["info", "low", "medium", "high", "critical"]

    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "reports" / "severity_policy.yaml", critical=True, root=PATHS.config_root / "reports")
        configured = self.policy.get("severity_order", [])
        if isinstance(configured, list) and configured:
            self.ORDER = [str(item) for item in configured]

    def classify(self, requested: str, evidence: list[EvidenceCitation], *, inference_only: bool = False, tags: list[str] | None = None) -> tuple[str, float]:
        tags = tags or []
        severity = requested if requested in self.ORDER else "info"
        confidence = self.confidence(evidence)
        if not evidence:
            severity = self._min(severity, "low")
            confidence = min(confidence, 0.25)
        if inference_only:
            severity = self._min(severity, "low")
            confidence = min(confidence, 0.35)
        if severity == "critical" and not self._critical_allowed(evidence, tags):
            severity = "high" if len(evidence) >= 2 else "medium"
        if severity == "high" and len(evidence) < 2:
            severity = "medium"
        return severity, confidence

    def confidence(self, evidence: list[EvidenceCitation]) -> float:
        if len(evidence) >= 2:
            return 0.9
        if len(evidence) == 1:
            return max(0.5, min(0.75, evidence[0].confidence))
        return 0.0

    def _critical_allowed(self, evidence: list[EvidenceCitation], tags: list[str]) -> bool:
        required = set(self.policy.get("rules", {}).get("critical_requires", []) if isinstance(self.policy.get("rules", {}), dict) else [])
        return len(evidence) >= 2 and bool(required.intersection(tags))

    def _min(self, current: str, maximum: str) -> str:
        return current if self.ORDER.index(current) <= self.ORDER.index(maximum) else maximum

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "severity_classifier", "severity_order": self.ORDER}
