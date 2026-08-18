from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.evaluation.fallback_decision import FallbackDecision
from aipinho.utils.yaml_loader import load_yaml_file


class FallbackPolicyService:
    SAFE_MESSAGES = {
        "deterministic_speaker": "Nao consegui aceitar a resposta do modelo com seguranca. Vou responder de forma deterministica e sem usar a saida insegura.",
        "deterministic_report": "O relatorio deterministico foi preservado porque a saida do modelo nao passou na avaliacao.",
        "policy_preview": "A pre-visualizacao de policy foi preservada; a saida do modelo nao foi usada para executar nada.",
        "safe_error": "A saida do modelo foi bloqueada por validacao. Nenhuma acao foi executada.",
        "stub": "Fallback para stub seguro sem inferencia real.",
    }

    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "evaluation" / "fallback_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def decide(self, *, purpose: str, status: str, violations: list[str], real_inference: bool = False) -> FallbackDecision:
        fallback = self.config.get("fallback", {}) if isinstance(self.config.get("fallback", {}), dict) else {}
        if status in {"accepted", "accepted_with_warnings"}:
            return FallbackDecision(should_fallback=False, fallback_type="none")
        if not fallback.get("enabled", True):
            return FallbackDecision(should_fallback=False, fallback_type="none", reason="fallback_disabled")
        if real_inference and fallback.get("never_fallback_to_unvalidated_real_model", True):
            fallback_type = "safe_error"
        else:
            by_purpose = self.config.get("by_purpose", {}) if isinstance(self.config.get("by_purpose", {}), dict) else {}
            fallback_type = str((by_purpose.get(purpose, {}) or {}).get("fallback", "safe_error"))
        reason = violations[0] if violations else status
        return FallbackDecision(should_fallback=True, fallback_type=fallback_type, reason=reason, safe_message=self.SAFE_MESSAGES.get(fallback_type, self.SAFE_MESSAGES["safe_error"]))

    def status(self) -> dict[str, object]:
        fallback = self.config.get("fallback", {}) if isinstance(self.config.get("fallback", {}), dict) else {}
        return {"status": "ok", "service": "fallback_policy", "enabled": bool(fallback.get("enabled", True))}
