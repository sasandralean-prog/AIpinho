from __future__ import annotations

import unicodedata
import re
from dataclasses import dataclass, field
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ContextPromptPolicyDecision:
    allowed: bool = True
    reason_code: str = "none"
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


class ContextPromptPolicyService:
    """Canonical prompt-level policy for governed context usage.

    The service does not perform retrieval, memory reads, prompt assembly, or
    execution. It only blocks prompt instructions that would bypass governed
    context, citation, provenance, or automatic-injection constraints.
    """

    def __init__(
        self,
        *,
        prompt_policy: dict[str, Any] | None = None,
        chat_response_policy: dict[str, Any] | None = None,
        rag_memory_policy: dict[str, Any] | None = None,
    ) -> None:
        self.prompt_policy = prompt_policy or load_yaml_file(
            PATHS.config_root / "context" / "context_prompt_injection_policy.yaml",
            critical=True,
            root=PATHS.config_root / "context",
        )
        self.chat_response_policy = chat_response_policy or load_yaml_file(
            PATHS.config_root / "ux" / "chat_response_policy.yaml",
            critical=True,
            root=PATHS.config_root / "ux",
        )
        self.rag_memory_policy = rag_memory_policy or load_yaml_file(
            PATHS.config_root / "rag" / "integration" / "rag_memory_policy.yaml",
            critical=True,
            root=PATHS.config_root / "rag" / "integration",
        )

    def evaluate_user_message(self, message: str) -> ContextPromptPolicyDecision:
        prompt_cfg = self._prompt_config()
        if not bool(prompt_cfg.get("enabled", True)):
            return ContextPromptPolicyDecision()

        normalized = self._normalize(message)
        if not normalized:
            return ContextPromptPolicyDecision()

        citation_decision = self._evaluate_citation_bypass(normalized, prompt_cfg)
        if not citation_decision.allowed:
            return citation_decision

        auto_context_decision = self._evaluate_automatic_context(normalized, prompt_cfg)
        if not auto_context_decision.allowed:
            return auto_context_decision

        return ContextPromptPolicyDecision()

    def _evaluate_citation_bypass(self, normalized: str, prompt_cfg: dict[str, Any]) -> ContextPromptPolicyDecision:
        cfg = self._dict(prompt_cfg.get("citation_bypass"))
        if not bool(cfg.get("enabled", True)):
            return ContextPromptPolicyDecision()
        if not bool(((self.chat_response_policy.get("retrieval") or {}).get("block_citation_bypass", True))):
            return ContextPromptPolicyDecision()

        citation_terms = self._terms(cfg.get("citation_terms"))
        bypass_terms = self._terms(cfg.get("bypass_terms"))
        if not (
            self._contains_any(normalized, citation_terms)
            and self._contains_citation_bypass(normalized, citation_terms, bypass_terms)
        ):
            return ContextPromptPolicyDecision()

        return ContextPromptPolicyDecision(
            allowed=False,
            reason_code=str(cfg.get("block_reason_code") or "context_citation_bypass_blocked"),
            message=str(
                cfg.get("message")
                or "Governed context requires citations, source scope, provenance, and a valid citation map."
            ),
            warnings=self._strings(cfg.get("warnings")) or ["context_citations_required", "citation_bypass_blocked"],
            evidence=["citation_term_detected", "bypass_term_detected", "context_prompt_policy"],
        )

    def _evaluate_automatic_context(self, normalized: str, prompt_cfg: dict[str, Any]) -> ContextPromptPolicyDecision:
        cfg = self._dict(prompt_cfg.get("automatic_context"))
        if not bool(cfg.get("enabled", True)):
            return ContextPromptPolicyDecision()

        retrieval_cfg = self.chat_response_policy.get("retrieval") or {}
        usage_modes = self.rag_memory_policy.get("usage_modes") or {}
        automatic_chat = usage_modes.get("automatic_chat") or {}
        auto_retrieval_allowed = bool(retrieval_cfg.get("allow_auto_retrieval", False))
        automatic_chat_enabled = bool(automatic_chat.get("enabled", False))
        if auto_retrieval_allowed and automatic_chat_enabled:
            return ContextPromptPolicyDecision()

        context_terms = self._terms(cfg.get("context_terms"))
        automatic_terms = self._terms(cfg.get("automatic_terms"))
        if not (self._contains_any(normalized, context_terms) and self._contains_any(normalized, automatic_terms)):
            return ContextPromptPolicyDecision()

        return ContextPromptPolicyDecision(
            allowed=False,
            reason_code=str(cfg.get("block_reason_code") or "automatic_context_injection_blocked"),
            message=str(
                cfg.get("message")
                or "Automatic context injection is disabled; use governed explicit retrieval with citations."
            ),
            warnings=self._strings(cfg.get("warnings"))
            or ["auto_memory_disabled", "rag_disabled", "prompt_memory_auto_injection_disabled"],
            evidence=["context_capability_term_detected", "automatic_mode_term_detected", "context_prompt_policy"],
        )

    def _prompt_config(self) -> dict[str, Any]:
        return self._dict(self.prompt_policy.get("prompt_injection"))

    def _terms(self, value: Any) -> list[str]:
        return [self._normalize(item) for item in self._strings(value) if self._normalize(item)]

    @staticmethod
    def _strings(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value]
        return []

    @staticmethod
    def _dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _contains_any(normalized: str, terms: list[str]) -> bool:
        return any(term and term in normalized for term in terms)

    @staticmethod
    def _contains_citation_bypass(normalized: str, citation_terms: list[str], bypass_terms: list[str]) -> bool:
        citation_group = "|".join(re.escape(term) for term in citation_terms if term)
        if not citation_group:
            return False
        for term in bypass_terms:
            if not term:
                continue
            if term in {"sem", "without"}:
                if re.search(rf"\b{re.escape(term)}\b(?:\s+\w+){{0,3}}\s+(?:{citation_group})\b", normalized):
                    return True
                continue
            if term in normalized:
                return True
        return False

    @staticmethod
    def _normalize(value: Any) -> str:
        decomposed = unicodedata.normalize("NFKD", str(value or ""))
        ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
        return " ".join(ascii_text.casefold().split())
