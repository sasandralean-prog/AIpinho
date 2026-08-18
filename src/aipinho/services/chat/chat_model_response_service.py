from __future__ import annotations

from typing import Any

from aipinho.schemas.chat.chat_evaluation_metadata import ChatEvaluationMetadata
from aipinho.schemas.chat.chat_fallback_metadata import ChatFallbackMetadata
from aipinho.schemas.chat.chat_model_metadata import ChatModelMetadata
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.chat.chat_model_fallback_service import ChatModelFallbackService
from aipinho.services.models.model_output_sanitizer import ModelOutputSanitizer


class ChatModelResponseService:
    ACCEPTED = {"accepted", "accepted_with_warnings"}

    def __init__(self, fallback_service: ChatModelFallbackService | None = None, sanitizer: ModelOutputSanitizer | None = None) -> None:
        self.fallback_service = fallback_service or ChatModelFallbackService()
        self.sanitizer = sanitizer or ModelOutputSanitizer()

    def convert(self, response: ModelResponse, *, profile_id: str | None = None) -> dict[str, Any]:
        evaluation = response.evaluation_result or {}
        status = str(evaluation.get("status", "accepted" if response.status == "completed" else response.status)) if isinstance(evaluation, dict) else response.status
        fallback_decision = evaluation.get("fallback_decision", {}) if isinstance(evaluation, dict) else {}
        fallback_required = bool(fallback_decision.get("should_fallback")) if isinstance(fallback_decision, dict) else status not in self.ACCEPTED
        accepted = response.status == "completed" and status in self.ACCEPTED and not fallback_required
        eval_meta = ChatEvaluationMetadata(
            evaluation_id=str(evaluation.get("evaluation_id")) if isinstance(evaluation, dict) and evaluation.get("evaluation_id") else None,
            status=status,
            score=float(evaluation.get("score")) if isinstance(evaluation, dict) and evaluation.get("score") is not None else None,
            accepted=accepted,
            fallback_required=fallback_required,
            violations=[str(item) for item in evaluation.get("violations", [])] if isinstance(evaluation, dict) else [],
            warnings=[str(item) for item in evaluation.get("warnings", [])] if isinstance(evaluation, dict) else [],
        )
        model_meta = ChatModelMetadata(
            model_id=response.model_id,
            provider_id=response.provider_id,
            profile_id=profile_id,
            real_inference=response.real_inference,
            process_started=response.real_inference,
            warnings=list(response.warnings),
        )
        if accepted:
            return {
                "status": "ok",
                "message": self.sanitizer.sanitize(response.content),
                "model": model_meta,
                "evaluation": eval_meta,
                "fallback": ChatFallbackMetadata(fallback_used=False, rejected_model_content_hidden=True),
                "warnings": list(dict.fromkeys([*response.warnings, *eval_meta.warnings])),
            }
        fallback = self.fallback_service.build(",".join(eval_meta.violations or response.warnings or [status]), status="fallback")
        return {
            "status": "fallback" if response.status != "blocked" else "blocked",
            "message": fallback.safe_message or "Resposta segura indisponivel.",
            "model": model_meta,
            "evaluation": eval_meta,
            "fallback": fallback,
            "warnings": list(dict.fromkeys([*response.warnings, *eval_meta.warnings, "model_output_hidden_by_fallback"])),
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "chat_model_response", "accepted_statuses": sorted(self.ACCEPTED)}
