from __future__ import annotations

from aipinho.schemas.interaction.contracts import ChatMessageRecord
from aipinho.schemas.mobile_view_models import HumanizedCard, MobileChatPresentation
from aipinho.services.mobile_view_models.chat_timeline_presenter import ChatTimelinePresenter


class MobilePresentationMapper:
    def __init__(self, chat_presenter: ChatTimelinePresenter | None = None) -> None:
        self.chat_presenter = chat_presenter or ChatTimelinePresenter()

    def chat(self, *, session_id: str | None, messages: list[ChatMessageRecord], cards: list[HumanizedCard]) -> MobileChatPresentation:
        return self.chat_presenter.present(session_id=session_id, messages=messages, cards=cards)
