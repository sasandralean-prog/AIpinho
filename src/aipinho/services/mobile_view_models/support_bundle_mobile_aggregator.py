from __future__ import annotations

from aipinho.schemas.mobile_view_models import MobileSupportBundlePreview
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper


class SupportBundleMobileAggregator:
    def __init__(self) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()

    def preview(self) -> MobileSupportBundlePreview:
        card = self.cards.card(
            card_id="support_bundle_preview",
            screen="debugger",
            card_type="support_bundle_preview",
            title="Support Bundle Preview",
            status="pending",
            severity="info",
            happening="Support bundle esta em preview sanitizado.",
            why="Preview permite revisar escopo antes de gerar artifact.",
            safety="safe",
            safety_reason="Sem raw inseguro, sem side effect operacional.",
            actions=["Revisar preview.", "Copiar manifesto sanitizado."],
            evidence=[self.evidence.ref("artifact", "support_bundle_preview", "support bundle preview")],
            metadata={"side_effect": False, "raw_included": False},
        )
        return MobileSupportBundlePreview(
            status="pending",
            cards=[card],
            artifact_preview={"kind": "support_bundle", "policy": "sanitized_preview_only"},
            sanitized=True,
            side_effect=False,
        )

