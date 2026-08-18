from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class PromptTemplate(AIpinhoModel):
    role_id: str
    instruction: str
