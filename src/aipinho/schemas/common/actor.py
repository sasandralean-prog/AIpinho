from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

ActorType = Literal["user", "system"]


class Actor(AIpinhoModel):
    type: ActorType = "system"
    id: str = "local_system"