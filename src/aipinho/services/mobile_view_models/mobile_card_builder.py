from __future__ import annotations

from aipinho.schemas.mobile_view_models import EvidenceRef, HumanizedCard, SafeUiAction
from aipinho.services.mobile_view_models.mobile_humanizer_service import MobileHumanizerService
from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder
from aipinho.services.mobile_view_models.mobile_sanitizer_service import MobileSanitizerService


class MobileCardBuilder:
    def __init__(self) -> None:
        self.humanizer = MobileHumanizerService()
        self.actions = MobileSafeActionBuilder()
        self.sanitizer = MobileSanitizerService()

    def card(
        self,
        *,
        card_id: str,
        screen: str,
        card_type: str,
        title: str,
        status: str,
        severity: str,
        happening: str,
        why: str,
        safety: str,
        safety_reason: str,
        actions: list[str],
        evidence: list[EvidenceRef],
        metadata: dict[str, object] | None = None,
        safe_actions: list[SafeUiAction] | None = None,
        raw_ref: str | None = None,
        trace_id: str | None = None,
        event_ids: list[str] | None = None,
    ) -> HumanizedCard:
        clean_metadata = self.sanitizer.sanitize_map(metadata or {})
        card = HumanizedCard(
            card_id=card_id,
            screen=screen,  # type: ignore[arg-type]
            card_type=card_type,
            title=self.sanitizer.sanitize_text(title),
            severity=severity,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            answers=self.humanizer.answers(
                happening=self.sanitizer.sanitize_text(happening),
                why=self.sanitizer.sanitize_text(why),
                safety=safety,
                safety_reason=self.sanitizer.sanitize_text(safety_reason),
                actions=[self.sanitizer.sanitize_text(action) for action in actions],
                evidence=evidence,
            ),
            metadata=clean_metadata,
            evidence=evidence,
            safe_actions=(safe_actions or []) + [self.actions.copy(card_id)],
            raw_ref=raw_ref,
            trace_id=trace_id,
            event_ids=event_ids or [],
        )
        card.copy_payload["raw_available"] = bool(raw_ref)
        card.copy_payload["copy_policy"] = "raw_ref_only" if raw_ref else "sanitized_only"
        return card
