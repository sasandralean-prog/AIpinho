from __future__ import annotations

from aipinho.schemas.mobile_view_models import HumanizedCard
from aipinho.services.mobile_view_models.mobile_sanitizer_service import MobileSanitizerService


class HumanCardRenderer:
    def __init__(self, sanitizer: MobileSanitizerService | None = None) -> None:
        self.sanitizer = sanitizer or MobileSanitizerService()

    def safety_label(self, card: HumanizedCard) -> str:
        answer = card.answers.is_it_safe.answer
        return {
            "safe": "Seguro",
            "caution": "Atenção",
            "risky": "Risco",
            "blocked": "Bloqueado",
            "unknown": "Indefinido",
        }.get(str(answer), "Indefinido")

    def normal_summary(self, card: HumanizedCard) -> str:
        happening = self.sanitizer.sanitize_text(card.answers.what_is_happening)
        why = self.sanitizer.sanitize_text(card.answers.why_is_it_happening)
        if happening and why:
            return f"{happening}\n{why}"
        return happening or why or card.title

    def has_real_evidence(self, card: HumanizedCard) -> bool:
        return any(self._real_ref(str(item.ref_id)) for item in card.evidence)

    def _real_ref(self, ref_id: str) -> bool:
        value = ref_id.strip().lower()
        return bool(value) and value not in {"latest", "null", "none", "unknown"}
