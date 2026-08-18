from __future__ import annotations

from aipinho.schemas.roles.role_fallback import RoleFallback


class RoleFallbackService:
    def deterministic_output(self, role_id: str, reason: str = "deterministic_only") -> RoleFallback:
        messages = {
            "supervisor": "Validacao deterministica: nenhum efeito colateral foi executado; role operou apenas dentro do contrato.",
            "debugger": "Resumo tecnico deterministico: trace disponivel, raw oculto e nenhuma tool executada.",
            "interpreter": "Interpretacao segura: estado analisado sem executar acoes.",
            "speaker": "Nao consegui obter uma resposta modelada segura; mantive uma resposta humana segura.",
            "analyst": '{"findings": [], "limitations": ["safe_empty_findings_no_evidence"]}',
        }
        return RoleFallback(fallback_used=True, fallback_type="deterministic_summary", message=messages.get(role_id, f"Fallback seguro: {reason}"))

    def safe_empty_findings(self) -> RoleFallback:
        return RoleFallback(fallback_used=True, fallback_type="safe_empty_findings", message='{"findings": [], "limitations": ["no_evidence_available"]}')

    def speaker_safe_error(self, reason: str) -> RoleFallback:
        return RoleFallback(fallback_used=True, fallback_type="speaker_safe_error", message=f"Nao consegui concluir esta etapa com seguranca: {reason}")

    def skip_optional_pass(self, reason: str) -> RoleFallback:
        return RoleFallback(fallback_used=True, fallback_type="skip_optional_pass", message=reason, skip_pass=True)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_fallback", "real_inference": False}
