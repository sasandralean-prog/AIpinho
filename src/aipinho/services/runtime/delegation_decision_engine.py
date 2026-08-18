from __future__ import annotations

import re
from typing import Any

from aipinho.schemas.runtime.delegation_contract import DelegationDecisionResult


class DelegationDecisionEngine:
    """Provider-neutral decision point for direct vs delegated responses."""

    DELEGATE_RE = re.compile(
        r"\b("
        r"pergunt(e|ar|a)?\s+(a|à)\s+aipinho|"
        r"consulte\s+(a|o)?\s*aipinho|"
        r"delegu(e|ar|e para)|"
        r"use\s+a\s+aipinho|"
        r"ai?pinho\s+(responda|execute|analise)|"
        r"consulte\s+o\s+projeto|"
        r"analise\s+o\s+projeto|"
        r"execute\s+pela\s+aipinho"
        r")\b",
        re.IGNORECASE,
    )
    APPROVAL_RE = re.compile(r"\b(shell|patch|escrev|write|delete|delet|instal|build|compil)\b", re.IGNORECASE)
    SIMPLE_DIRECT_RE = re.compile(r"^\s*(quanto\s+e|quanto\s+é|what\s+is)?\s*\d+\s*[\+\-\*/]\s*\d+\s*\??\s*$", re.IGNORECASE)

    def decide(
        self,
        *,
        prompt: str,
        provider: str = "external_adapter",
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DelegationDecisionResult:
        text = str(prompt or "")
        context = context or {}
        metadata = metadata or {}
        forced = str(metadata.get("delegation_mode") or context.get("delegation_mode") or "").upper()
        if forced in {"DIRECT_RESPONSE", "DELEGATE", "HYBRID", "BLOCK", "REQUIRES_APPROVAL"}:
            return DelegationDecisionResult(
                decision=forced,  # type: ignore[arg-type]
                reason_code=f"forced_{forced.lower()}",
                reason="Delegation mode explicitly supplied by governed metadata.",
                requires_delegation_contract=forced in {"DELEGATE", "HYBRID"},
                requires_approval=forced == "REQUIRES_APPROVAL",
                blocked=forced == "BLOCK",
                evidence=["metadata_override"],
                metadata={"provider": provider},
            )
        if self.SIMPLE_DIRECT_RE.search(text):
            return DelegationDecisionResult(
                decision="DIRECT_RESPONSE",
                reason_code="simple_direct_query",
                reason="Simple answerable prompt does not require AIpinho runtime delegation.",
                evidence=["simple_direct_signal"],
                metadata={"provider": provider},
            )
        if self.DELEGATE_RE.search(text):
            return DelegationDecisionResult(
                decision="DELEGATE",
                reason_code="explicit_delegation_requested",
                reason="Prompt asks the adapter to consult or delegate to AIpinho.",
                requires_delegation_contract=True,
                evidence=["delegate_signal"],
                metadata={"provider": provider},
            )
        if self.APPROVAL_RE.search(text) and not context.get("executable_plan_ref"):
            return DelegationDecisionResult(
                decision="REQUIRES_APPROVAL",
                reason_code="side_effect_requires_governed_plan",
                reason="Potential side effect requires an executable plan and approval before runtime delegation.",
                requires_approval=True,
                evidence=["side_effect_signal"],
                metadata={"provider": provider},
            )
        return DelegationDecisionResult(
            decision="DIRECT_RESPONSE",
            reason_code="no_delegation_signal",
            reason="No explicit delegation requirement detected.",
            evidence=["direct_response_default"],
            metadata={"provider": provider},
        )
