from __future__ import annotations

from aipinho.schemas.mobile_view_models import EvidenceBundleView
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper


class EvidenceMobileAggregator:
    def __init__(self) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()

    def view_model(self, evidence_type: str, ref_id: str) -> EvidenceBundleView:
        card = self.cards.card(
            card_id=f"evidence_{evidence_type}_{ref_id}".replace("/", "_"),
            screen="debugger",
            card_type="evidence_bundle",
            title="Evidencia sanitizada",
            status="unknown",
            severity="info",
            happening=f"Evidencia {evidence_type} foi solicitada por referencia.",
            why="O mobile abre evidencia por ref_id, nao por raw dump.",
            safety="safe",
            safety_reason="Payload sanitizado e sem secrets por padrao.",
            actions=["Copiar evidencia sanitizada.", "Abrir trace se disponivel."],
            evidence=[self.evidence.ref(evidence_type, ref_id, f"{evidence_type}:{ref_id}")],
            metadata={"raw_default_visible": False},
        )
        return EvidenceBundleView(evidence_type=evidence_type, ref_id=ref_id, status="unknown", cards=[card], sanitized=True)

