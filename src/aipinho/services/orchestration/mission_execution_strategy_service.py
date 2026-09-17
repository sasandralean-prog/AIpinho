from __future__ import annotations

import unicodedata
from typing import Any

from aipinho.schemas.runtime.mission_contract import MissionExecutionMode


class MissionExecutionStrategyService:
    """Derives mission continuation intent at semantic ingress only."""

    _END_TO_END_TERMS = (
        "end-to-end",
        "end to end",
        "fim a fim",
        "missao inteira",
        "missão inteira",
        "missao completa",
        "missão completa",
        "uma unica missao",
        "uma única missão",
        "autonomamente",
        "ate concluir",
        "até concluir",
    )
    _STAGED_TERMS = (
        "pare depois",
        "parar depois",
        "somente esta fase",
        "só esta fase",
        "apenas esta fase",
        "nao continue sem",
        "não continue sem",
        "depois eu aprovo",
        "aguarde minha aprovacao",
        "aguarde minha aprovação",
    )

    def resolve(
        self,
        *,
        prompt: str,
        semantic_graph: dict[str, Any] | Any | None = None,
    ) -> MissionExecutionMode:
        text = self._normalize(prompt)
        if any(self._normalize(term) in text for term in self._STAGED_TERMS):
            return "staged"
        if any(self._normalize(term) in text for term in self._END_TO_END_TERMS):
            return "end_to_end_governed"
        graph = self._graph(semantic_graph)
        if (
            bool(graph.get("mutation_intent"))
            and bool(graph.get("execution_intent"))
            and self._looks_like_multi_phase_repair(text)
        ):
            return "end_to_end_governed"
        return "single_operation"

    def _looks_like_multi_phase_repair(self, text: str) -> bool:
        repair = any(term in text for term in ("corrij", "corrig", "repar", "consert", "fix ", "repair"))
        validate = any(term in text for term in ("test", "valid", "build", "compile", "compil"))
        return repair and validate

    def _graph(self, value: dict[str, Any] | Any | None) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return dict(value.model_dump(mode="json"))
        return {}

    def _normalize(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
