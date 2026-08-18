from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

ChatMode = Literal["normal", "preview", "debug"]
ChatSurface = Literal["api", "mobile", "workbench", "cli", "unknown"]


class ChatContext(AIpinhoModel):
    active_workspace: str | None = None
    active_task_id: str | None = None
    surface: ChatSurface = "unknown"
    cognitive_readiness_id: str | None = None
    phase0_result_ref: str | None = None
    phase0_prediction_id: str | None = None
    phase0_decision: str | None = None


class ChatRequest(AIpinhoModel):
    message: str
    session_id: str | None = None
    user_id: str | None = None
    mode: ChatMode = "normal"
    include_trace: bool = False
    context: ChatContext | None = None
    use_model_stub: bool = False
    model_id: str | None = None
