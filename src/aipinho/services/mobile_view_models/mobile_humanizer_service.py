from __future__ import annotations

from aipinho.schemas.mobile_view_models import EvidenceRef, HumanizedAnswerSet, SafetyState


class MobileHumanizerService:
    def answers(
        self,
        *,
        happening: str,
        why: str,
        safety: str = "unknown",
        safety_reason: str = "Estado derivado de dados sanitizados do backend.",
        actions: list[str] | None = None,
        evidence: list[EvidenceRef] | None = None,
        copy_available: bool = True,
    ) -> HumanizedAnswerSet:
        return HumanizedAnswerSet(
            what_is_happening=happening,
            why_is_it_happening=why,
            is_it_safe=SafetyState(answer=safety, reason=safety_reason),  # type: ignore[arg-type]
            what_can_i_do_now=actions or ["Atualizar view-model.", "Copiar resumo sanitizado."],
            what_evidence_supports_this=evidence or [],
            can_copy_sanitized_summary=copy_available,
        )

