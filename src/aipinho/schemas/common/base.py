from __future__ import annotations

from pydantic import BaseModel

try:
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover - Pydantic v1 fallback
    ConfigDict = None  # type: ignore[assignment]


if ConfigDict is not None:
    class AIpinhoModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
else:  # pragma: no cover - Pydantic v1 fallback
    class AIpinhoModel(BaseModel):
        class Config:
            extra = "forbid"