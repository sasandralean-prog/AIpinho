from __future__ import annotations

from aipinho.schemas.external_collaboration import (
    ExternalAdapterEvaluationOutput,
    ExternalAdapterEvaluationRequest,
    ExternalAdapterOutput,
    ExternalAdapterReviewRequest,
    ExternalReviewCreateRequest,
    ExternalReviewFinding,
    SuccessEvaluationCreateRequest,
)
from aipinho.services.external_speaker_truth_auditor import ExternalSpeakerTruthAuditor
from aipinho.services.runtime.delegation_truth_validator import DelegationTruthValidator


class ExternalAdapter:
    adapter_id = "generic"

    def adapt_review(self, request: ExternalAdapterReviewRequest) -> ExternalAdapterOutput:
        summary = self._clean_text(request.provider_output)
        audit = ExternalSpeakerTruthAuditor().audit(summary)
        delegation = DelegationTruthValidator().validate(
            summary,
            delegation_id=str(request.metadata.get("delegation_id") or "") or None,
        )
        violations = list(dict.fromkeys([*audit.violations, *delegation.violations]))
        machine = ExternalReviewCreateRequest(
            provider=request.provider or self.adapter_id,
            task_run_id=request.task_run_id,
            external_task_id=request.external_task_id,
            conversation_id=request.conversation_id,
            status="submitted" if not violations else "review_loop_required",
            confidence=request.confidence,
            findings=[
                ExternalReviewFinding(
                    severity="warning" if violations else "info",
                    summary=summary[:500] or "External review received.",
                    recommendation="AIpinho deve pedir nova revisao externa em modo Auditor."
                    if violations
                    else None,
                )
            ],
            recommendations=[],
            missing_evidence=violations,
            next_action="review_loop" if violations else "aipinho_decides",
            raw_summary=summary[:3000],
            metadata={
                "adapter_id": self.adapter_id,
                "speaker_truth_mode": "auditor",
                "speaker_truth_audit": audit.__dict__,
                "delegation_truth": delegation.model_dump(),
                **request.metadata,
            },
        )
        return ExternalAdapterOutput(
            adapter_id=self.adapter_id,
            human_output=self._human_output(audit, delegation),
            machine_output=machine,
            metadata={
                "machine_contract": "external_review.v1",
                "speaker_truth_audit": audit.__dict__,
                "delegation_truth": delegation.model_dump(),
            },
        )

    def adapt_success_evaluation(self, request: ExternalAdapterEvaluationRequest) -> ExternalAdapterEvaluationOutput:
        summary = self._clean_text(request.provider_output)
        audit = ExternalSpeakerTruthAuditor().audit(summary)
        delegation = DelegationTruthValidator().validate(
            summary,
            delegation_id=str(request.metadata.get("delegation_id") or "") or None,
        )
        blocking = self._blocking_findings(summary)
        if audit.violations or delegation.violations:
            blocking = list(dict.fromkeys([*blocking, *audit.violations, *delegation.violations]))
        machine = SuccessEvaluationCreateRequest(
            provider=request.provider or self.adapter_id,
            session_id=request.session_id,
            task_run_id=request.task_run_id,
            external_task_id=request.external_task_id,
            status="submitted",
            acceptance_score=self._acceptance_score(summary, blocking),
            blocking_findings=blocking,
            recommendations=self._recommendations_from_text(summary),
            confidence=request.confidence,
            needs_retry=bool(blocking) or audit.decision in {"request_new_execution", "detect_inconsistency"},
            ready=not blocking and audit.decision == "approve" and self._has_ready_signal(summary),
            needs_human=False,
            next_action="aipinho_decides",
            metadata={
                "adapter_id": self.adapter_id,
                "speaker_truth_mode": "auditor",
                "speaker_truth_audit": audit.__dict__,
                "delegation_truth": delegation.model_dump(),
                **request.metadata,
            },
        )
        return ExternalAdapterEvaluationOutput(
            adapter_id=self.adapter_id,
            human_output=self._human_output(audit, delegation),
            machine_output=machine,
            metadata={
                "machine_contract": "success_evaluation.v1",
                "speaker_truth_audit": audit.__dict__,
                "delegation_truth": delegation.model_dump(),
            },
        )

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(str(value or "").replace("\r", "\n").split())

    @staticmethod
    def _blocking_findings(text: str) -> list[str]:
        lowered = text.lower()
        markers = ("falhou", "failed", "erro", "error", "bloque", "missing", "falt")
        if any(marker in lowered for marker in markers):
            return [text[:500] or "External model reported a blocking issue."]
        return []

    @staticmethod
    def _has_ready_signal(text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in ("pronto", "ready", "conclu", "completed", "terminou", "passou"))

    @staticmethod
    def _acceptance_score(text: str, blocking: list[str]) -> float:
        if blocking:
            return 0.4
        return 0.9 if ExternalAdapter._has_ready_signal(text) else 0.6

    @staticmethod
    def _recommendations_from_text(text: str) -> list[str]:
        return []

    @staticmethod
    def _human_output(audit, delegation) -> str:
        if delegation.status == "violation":
            return (
                "SpeakerTruthViolation: provider afirmou delegacao sem delegation_id, "
                "child_run_id, polling e evidencia de runtime."
            )
        return ExternalSpeakerTruthAuditor.human_summary(audit)


class GeminiExternalAdapter(ExternalAdapter):
    adapter_id = "gemini"

    def adapt_review(self, request: ExternalAdapterReviewRequest) -> ExternalAdapterOutput:
        output = super().adapt_review(request.model_copy(update={"provider": request.provider or self.adapter_id}))
        provider_text = request.provider_output
        human = output.human_output or "Gemini retornou uma revisao externa para a AIpinho interpretar."
        machine = output.machine_output.model_copy(
            update={
                "provider": request.provider or self.adapter_id,
                "recommendations": self._recommendations_from_text(provider_text),
                "next_action": "aipinho_interpret_review",
                "metadata": {**output.machine_output.metadata, "external_provider_notice": True},
            }
        )
        return output.model_copy(update={"human_output": human, "machine_output": machine})

    def adapt_success_evaluation(self, request: ExternalAdapterEvaluationRequest) -> ExternalAdapterEvaluationOutput:
        output = super().adapt_success_evaluation(request.model_copy(update={"provider": request.provider or self.adapter_id}))
        provider_text = request.provider_output
        machine = output.machine_output.model_copy(
            update={
                "provider": request.provider or self.adapter_id,
                "recommendations": list(
                    dict.fromkeys([*output.machine_output.recommendations, *self._recommendations_from_text(provider_text)])
                ),
                "next_action": "aipinho_evaluate_success",
                "metadata": {**output.machine_output.metadata, "external_provider_notice": True},
            }
        )
        return output.model_copy(update={"machine_output": machine})

    @staticmethod
    def _recommendations_from_text(text: str) -> list[str]:
        lowered = text.lower()
        recommendations: list[str] = []
        if "build" in lowered or "compil" in lowered:
            recommendations.append("Revisar evidencias de build pela AIpinho antes de declarar sucesso.")
        if "apk" in lowered:
            recommendations.append("Confirmar artifact APK pela registry universal antes de entregar.")
        if "asset" in lowered or "assets" in lowered:
            recommendations.append("Validar assets pelo fluxo interno antes de aceitar a recomendacao externa.")
        return recommendations


class ExternalAdapterRegistry:
    def __init__(self, adapters: dict[str, ExternalAdapter] | None = None) -> None:
        self.adapters = adapters or {
            GeminiExternalAdapter.adapter_id: GeminiExternalAdapter(),
        }

    def get(self, adapter_id: str) -> ExternalAdapter | None:
        return self.adapters.get(adapter_id.strip().lower())

    def list_adapters(self) -> list[dict[str, str]]:
        return [{"adapter_id": key, "contracts": "external_review.v1,success_evaluation.v1"} for key in sorted(self.adapters)]
