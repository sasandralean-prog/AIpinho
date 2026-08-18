from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class TestRecommendation(AIpinhoModel):
    __test__ = False

    test_type: str
    command: str
    reason: str = ""
    execution_enabled: bool = False
