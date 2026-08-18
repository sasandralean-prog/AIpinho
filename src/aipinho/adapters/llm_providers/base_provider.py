from __future__ import annotations

from abc import ABC, abstractmethod

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse


class BaseModelProvider(ABC):
    @abstractmethod
    def status(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def invoke(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError
