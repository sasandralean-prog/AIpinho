from __future__ import annotations

from aipinho.schemas.mobile_view_models import HumanizedCard, SanitizedCopyPayload
from aipinho.services.mobile_view_models.mobile_sanitizer_service import MobileSanitizerService


class MobileCopyPayloadService:
    def __init__(self) -> None:
        self.sanitizer = MobileSanitizerService()

    def payload_for_card(self, card: HumanizedCard) -> SanitizedCopyPayload:
        summary = "\n".join(
            [
                card.title,
                f"O que esta acontecendo: {card.answers.what_is_happening}",
                f"Por que: {card.answers.why_is_it_happening}",
                f"Seguranca: {card.answers.is_it_safe.answer} - {card.answers.is_it_safe.reason}",
                "Acoes: " + "; ".join(card.answers.what_can_i_do_now),
            ]
        )
        sanitized_summary = self.sanitizer.sanitize_text(summary)
        return SanitizedCopyPayload(
            card_id=card.card_id,
            summary=sanitized_summary,
            metadata=self.sanitizer.sanitize_map(card.metadata),
            evidence=card.evidence,
            copy_policy=str(card.copy_payload.get("copy_policy", "sanitized_only")),  # type: ignore[arg-type]
            contains_secret=self.sanitizer.contains_secret(summary),
        )
