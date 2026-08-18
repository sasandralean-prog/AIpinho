from __future__ import annotations

from uuid import uuid5, NAMESPACE_URL

from aipinho.core.paths import PATHS
from aipinho.schemas.reports.evidence_finding import EvidenceFinding
from aipinho.schemas.reports.recommendation import Recommendation
from aipinho.utils.yaml_loader import load_yaml_file


class RecommendationService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "reports" / "recommendation_policy.yaml", critical=True, root=PATHS.config_root / "reports")

    def build_for_finding(self, finding: EvidenceFinding) -> Recommendation:
        text = self._safe_text(finding.recommendation)
        requires_followup = finding.requires_followup or self._mentions_write(text)
        return Recommendation(
            recommendation_id=f"recommendation_{uuid5(NAMESPACE_URL, finding.finding_id + ':' + text).hex}",
            finding_id=finding.finding_id,
            title=f"Recomendacao: {finding.title}",
            summary=text,
            requires_write=False,
            requires_followup=requires_followup,
            safe_next_actions=self._safe_actions(requires_followup),
        )

    def apply_to_finding(self, finding: EvidenceFinding) -> EvidenceFinding:
        recommendation = self._safe_text(finding.recommendation)
        finding.recommendation = recommendation
        if self._mentions_write(recommendation):
            finding.requires_followup = True
            finding.requires_write = False
        return finding

    def _safe_text(self, text: str) -> str:
        value = text.strip() or "Registrar acompanhamento em sprint futuro com teste e evidencia."
        if not bool(self.policy.get("recommendations", {}).get("allow_patch_instruction", False)):
            value = value.replace("aplicar patch", "planejar correcao futura com preview e approval")
            value = value.replace("apply patch", "plan future correction with preview and approval")
        return value

    def _mentions_write(self, text: str) -> bool:
        keywords = self.policy.get("recommendations", {}).get("write_keywords", []) if isinstance(self.policy.get("recommendations", {}), dict) else []
        lowered = text.lower()
        return any(str(keyword).lower() in lowered for keyword in keywords)

    def _safe_actions(self, requires_followup: bool) -> list[str]:
        if requires_followup:
            return ["future_sprint", "add_test", "review"]
        return ["document", "review"]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "recommendation_service"}
