from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Literal


MissionExecutionMode = Literal[
    "single_operation",
    "staged",
    "end_to_end_governed",
]


@dataclass(frozen=True)
class MissionExecutionStrategy:
    mode: MissionExecutionMode
    auto_continue: bool
    requires_new_prompt_between_phases: bool
    stop_at_approval_gate: bool
    rationale: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = list(self.evidence)
        return payload


class MissionExecutionStrategyService:
    """Derives mission continuation semantics from the current prompt contract.

    This service decides whether one user prompt authorizes a whole governed
    mission or only the current phase. Internal runtime phases are still allowed
    in end-to-end mode; the difference is whether a new user prompt is required
    between them.
    """

    _STAGED_TERMS = (
        "analise apenas",
        "apenas analise",
        "somente analise",
        "so analise",
        "somente diagnostique",
        "apenas diagnostique",
        "pare depois",
        "pare apos",
        "espere minha confirmacao",
        "aguarde minha confirmacao",
        "me mostre antes",
        "antes de alterar",
        "antes de modificar",
        "antes de executar",
        "nao execute",
        "sem executar",
        "nao aplique",
        "sem aplicar",
        "so planeje",
        "somente planeje",
        "apenas planeje",
    )

    _END_TO_END_TERMS = (
        "end to end",
        "ponta a ponta",
        "ate o fim",
        "continue ate concluir",
        "continue ate terminar",
        "execute tudo",
        "faca tudo",
        "nao pare no planejamento",
        "nao pare no diagnostico",
        "commit e git push",
        "faca commit e git push",
        "faça commit e git push",
    )

    def resolve(
        self,
        *,
        prompt: str,
        semantic_graph: dict[str, Any] | Any | None,
    ) -> MissionExecutionStrategy:
        graph = self._graph(semantic_graph)
        normalized = self._normalize(prompt)
        requested_effects = {
            str(item)
            for item in graph.get("requested_effects", []) or []
            if str(item)
        }
        has_side_effect_intent = bool(
            graph.get("mutation_intent")
            or graph.get("execution_intent")
            or requested_effects.intersection(
                {
                    "workspace_mutation",
                    "build_execution",
                    "runtime_execution",
                    "command_execution",
                }
            )
        )
        explicit_staged = [term for term in self._STAGED_TERMS if term in normalized]
        explicit_end_to_end = [
            term for term in self._END_TO_END_TERMS if term in normalized
        ]

        if explicit_staged:
            return MissionExecutionStrategy(
                mode="staged",
                auto_continue=False,
                requires_new_prompt_between_phases=True,
                stop_at_approval_gate=True,
                rationale="prompt_explicitly_limits_execution_to_current_phase",
                evidence=tuple(f"prompt:{term}" for term in explicit_staged),
            )

        if not has_side_effect_intent:
            return MissionExecutionStrategy(
                mode="single_operation",
                auto_continue=False,
                requires_new_prompt_between_phases=False,
                stop_at_approval_gate=False,
                rationale="prompt_has_no_future_side_effect_intent",
                evidence=("semantic_graph:no_side_effect_intent",),
            )

        if explicit_end_to_end or (
            bool(graph.get("mutation_intent"))
            and bool(graph.get("execution_intent"))
        ):
            evidence = [
                *(f"prompt:{term}" for term in explicit_end_to_end),
                "semantic_graph:mutation_intent"
                if graph.get("mutation_intent")
                else "",
                "semantic_graph:execution_intent"
                if graph.get("execution_intent")
                else "",
            ]
            return MissionExecutionStrategy(
                mode="end_to_end_governed",
                auto_continue=True,
                requires_new_prompt_between_phases=False,
                stop_at_approval_gate=True,
                rationale="prompt_authorizes_a_multi_phase_governed_mission",
                evidence=tuple(item for item in evidence if item),
            )

        return MissionExecutionStrategy(
            mode="staged",
            auto_continue=False,
            requires_new_prompt_between_phases=True,
            stop_at_approval_gate=True,
            rationale="side_effect_intent_exists_but_end_to_end_authority_is_not_explicit",
            evidence=("semantic_graph:side_effect_intent",),
        )

    def _graph(self, value: dict[str, Any] | Any | None) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            return dict(value.model_dump(mode="json"))
        return {}

    def _normalize(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
        return "".join(
            ch for ch in decomposed if not unicodedata.combining(ch)
        )
