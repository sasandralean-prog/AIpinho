from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LucioSafeFallbackDecision:
    category: str
    allowed: bool
    response_text: str = ""
    reasons: list[str] = field(default_factory=list)


class LucioSafeFallbackService:
    """Classify whether a failed direct provider call can use a local safe answer."""

    OPERATIONAL_MARKERS = {
        "crie",
        "criar",
        "edite",
        "editar",
        "altere",
        "alterar",
        "modifique",
        "corrija",
        "corrigir",
        "execute",
        "executar",
        "rode",
        "rodar",
        "salve em",
        "salve no",
        "salve na",
        "salvar",
        "grave",
        "gerar arquivo",
        "gerar patch",
        "aplique",
        "aplicar",
        "delete",
        "deletar",
        "remova",
        "remover",
        "build",
        "compile",
        "compilar",
        "teste",
        "testar",
    }
    NONTRIVIAL_MARKERS = {
        "profundamente",
        "fontes",
        "recentes",
        "recente",
        "atual",
        "noticias",
        "pesquise",
        "internet",
        "juridico",
        "medico",
        "financeiro",
        "arquitetura",
        "projeto",
        "diagnostique",
        "diagnosticar",
        "analise",
        "analisar",
        "estrategia",
        "estrategico",
    }
    GREETING_MARKERS = {
        "oi",
        "ola",
        "olá",
        "salve",
        "bom dia",
        "boa tarde",
        "boa noite",
        "tudo bem",
        "tudo certo",
        "e ai",
        "e aí",
    }
    HELP_MARKERS = {
        "ajuda",
        "me ajuda",
        "como usar",
        "o que voce faz",
        "o que você faz",
        "o que consegue fazer",
    }
    COLORS = {
        "branco",
        "branca",
        "preto",
        "preta",
        "azul",
        "verde",
        "vermelho",
        "vermelha",
        "amarelo",
        "amarela",
        "rosa",
        "roxo",
        "roxa",
        "cinza",
        "marrom",
        "laranja",
    }

    def classify(self, prompt: str, *, requires_local_execution: bool, requested_capabilities: list[str]) -> LucioSafeFallbackDecision:
        text = " ".join(str(prompt or "").strip().casefold().split())
        if not text:
            return LucioSafeFallbackDecision(category="nontrivial_requires_model", allowed=False, reasons=["empty_prompt"])
        if requires_local_execution or requested_capabilities:
            return LucioSafeFallbackDecision(category="operational_request", allowed=False, reasons=["local_execution_or_capability_requested"])
        if self._has_any(text, self.OPERATIONAL_MARKERS):
            return LucioSafeFallbackDecision(category="operational_request", allowed=False, reasons=["operational_marker_detected"])
        if self._is_trivial_color_fact(text):
            color = self._extract_color_from_question(text)
            return LucioSafeFallbackDecision(
                category="trivial_low_risk_fact",
                allowed=True,
                response_text=f"{color.capitalize()}.",
                reasons=["trivial_color_fact_pattern"],
            )
        if self._is_greeting(text):
            return LucioSafeFallbackDecision(
                category="greeting",
                allowed=True,
                response_text="Salve. Estou por aqui. O provider principal nao respondeu agora, entao usei uma resposta local segura.",
                reasons=["simple_greeting", "no_local_execution_required"],
            )
        if self._is_simple_help(text):
            return LucioSafeFallbackDecision(
                category="simple_help_request",
                allowed=True,
                response_text=(
                    "Posso ajudar em conversa, planejamento, revisao e encaminhamento governado. "
                    "O provider principal nao respondeu agora, entao mantive esta resposta local simples e segura."
                ),
                reasons=["simple_help_request", "no_external_facts_required"],
            )
        if self._has_any(text, self.NONTRIVIAL_MARKERS):
            return LucioSafeFallbackDecision(category="nontrivial_requires_model", allowed=False, reasons=["nontrivial_or_external_context_required"])
        return LucioSafeFallbackDecision(category="nontrivial_requires_model", allowed=False, reasons=["fallback_not_confident"])

    def _is_greeting(self, text: str) -> bool:
        words = re.findall(r"[\wÀ-ÿ]+", text)
        short_enough = len(words) <= 8
        return short_enough and self._has_any(text, self.GREETING_MARKERS)

    def _is_simple_help(self, text: str) -> bool:
        words = re.findall(r"[\wÀ-ÿ]+", text)
        return len(words) <= 10 and self._has_any(text, self.HELP_MARKERS)

    def _is_trivial_color_fact(self, text: str) -> bool:
        return "qual" in text and "cor" in text and self._extract_color_from_question(text) != ""

    def _extract_color_from_question(self, text: str) -> str:
        tokens = re.findall(r"[\wÀ-ÿ]+", text)
        for token in tokens:
            if token in self.COLORS:
                return token
        return ""

    @staticmethod
    def _has_any(text: str, markers: set[str]) -> bool:
        return any(marker in text for marker in markers)
