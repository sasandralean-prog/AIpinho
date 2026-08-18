from __future__ import annotations

import re

from aipinho.schemas.governance.lifecycle import CanonicalIntentDecision
from aipinho.services.governance.intent.canonical_intent_router import CanonicalIntentRouter
from aipinho.services.governance.intent.intent_normalizer import normalize_text


class SemanticIntentResolutionService:
    """Single semantic authority for prompt-level operational intent.

    Legacy chat and governance routes may adapt this decision to their public
    response contracts, but they should not independently reinterpret the prompt
    for approval, permission, read-only, shell, write, or project intent.
    """

    _PERMISSION_GRANT_TERMS = (
        "dou permissao",
        "dar permissao",
        "permissao para",
        "permissoes para",
        "concedo permissao",
        "autorizo",
        "permito",
        "pode escrever",
        "pode criar",
        "pode ler",
        "pode alterar",
        "pode modificar",
        "libere",
        "liberar",
        "habilite",
        "permitir",
    )
    _PERMANENT_PERMISSION_TERMS = ("permanente", "sempre", "config", "registry", "registrar")
    _PERMISSION_ACTION_PATTERNS = (
        r"\b(?:eu\s+)?dou permissao\b",
        r"\b(?:eu\s+)?concedo\s+permissao\b",
        r"\b(?:eu\s+)?autorizo\b",
        r"\b(?:eu\s+)?permito\b",
        r"\bpermissao\s+para\s+(?:ler|escrever|criar|alterar|modificar|rodar|executar)\b",
        r"\bautorizar\b",
        r"\bliberar\b",
        r"\blibere\b",
        r"\bhabilite\b",
        r"\bpermitir\b",
        r"\bpode\s+(?:escrever|criar|ler|alterar|modificar|rodar|executar)\b",
    )

    def __init__(self, router: CanonicalIntentRouter | None = None) -> None:
        self.router = router or CanonicalIntentRouter()

    def resolve(self, text: str, *, source_channel: str = "unknown") -> CanonicalIntentDecision:
        base = self.router.decide(text, source_channel=source_channel)
        if self._has_hard_precedence(base):
            return base

        normalized = normalize_text(text)
        if self._is_positive_permission_grant(normalized):
            permanent = any(term in normalized for term in self._PERMANENT_PERMISSION_TERMS)
            operation_type = "config_permission_grant" if permanent else "session_permission_grant"
            return CanonicalIntentDecision(
                intent_type="permission_grant_request",
                operation_type=operation_type,
                requires_task=False,
                side_effect_requested=False,
                readonly=False,
                source_channel=source_channel,
                evidence=["positive_permission_grant_signal", "semantic_intent_resolution"],
            )

        return base

    def _has_hard_precedence(self, decision: CanonicalIntentDecision) -> bool:
        if decision.intent_type == "approval_command":
            return True
        if decision.readonly and (
            decision.negative_constraints
            or decision.intent_type in {"product_planning_readonly", "workspace_analysis_readonly"}
        ):
            return True
        return False

    def _is_positive_permission_grant(self, normalized: str) -> bool:
        if re.search(r"\bnao\s+pode\s+(?:escrever|criar|ler|alterar|modificar|rodar|executar)\b", normalized):
            return False
        if not any(term in normalized for term in self._PERMISSION_GRANT_TERMS):
            return False
        return any(re.search(pattern, normalized) for pattern in self._PERMISSION_ACTION_PATTERNS)
