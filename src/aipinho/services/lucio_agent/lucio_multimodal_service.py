from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aipinho.schemas.lucio_agent import (
    LucioAgentRequest,
    LucioMultimodalMessage,
    LucioRouteDecision,
    LucioVisualArtifact,
)
from aipinho.schemas.vision.contracts import ImageInput, ImageSourceRef, VisionAnalysisRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.events.event_core import contains_secret, redact_payload
from aipinho.services.vision.vision_analysis_service import VisionAnalysisService


VISUAL_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
DOCUMENT_CONTENT_TYPES = {"application/pdf", "text/plain", "text/markdown", "application/json"}


@dataclass(frozen=True)
class LucioMultimodalContext:
    message: LucioMultimodalMessage
    visual_artifacts: list[LucioVisualArtifact]
    warnings: list[str]
    structured_summary: str
    evidence_refs: list[str]
    provider_context: str


class LucioMultimodalService:
    def __init__(
        self,
        *,
        gateway: AgentToolGatewayService | None = None,
        vision: VisionAnalysisService | None = None,
    ) -> None:
        self.gateway = gateway or AgentToolGatewayService()
        self.vision = vision or VisionAnalysisService()

    def build_context(self, request: LucioAgentRequest, decision: LucioRouteDecision | None = None) -> LucioMultimodalContext | None:
        if not request.artifacts:
            return None
        visual_artifacts = [self._visual_artifact(request.session_id, artifact.model_dump()) for artifact in request.artifacts]
        content_types = [item.content_type or "application/octet-stream" for item in visual_artifacts]
        image_ids = [item.artifact_id for item in visual_artifacts if self._is_visual(item.content_type)]
        file_ids = [item.artifact_id for item in visual_artifacts if not self._is_visual(item.content_type)]
        evidence_refs = [f"artifact:{item.artifact_id}" for item in visual_artifacts]
        warnings = self._warnings(visual_artifacts)
        redaction_status = self._redaction_status(visual_artifacts, warnings)
        message = LucioMultimodalMessage(
            session_id=request.session_id,
            user_text=request.prompt,
            artifact_refs=[item.artifact_id for item in visual_artifacts],
            image_artifact_ids=image_ids,
            file_artifact_ids=file_ids,
            content_types=content_types,
            user_goal=request.operation_type,
            privacy_level="sensitive_possible" if warnings else "public_safe",
            redaction_status=redaction_status,
            multimodal_capability_required=bool(image_ids),
            route_decision_id=decision.route_decision_id if decision else None,
            evidence_refs=evidence_refs,
        )
        summaries = [self._analyze_visual(item, request.prompt) for item in visual_artifacts if self._is_visual(item.content_type)]
        structured = self.structured_answer(request, visual_artifacts, summaries, warnings, decision)
        provider_context = self.provider_context(visual_artifacts, summaries, warnings, decision)
        return LucioMultimodalContext(
            message=message,
            visual_artifacts=visual_artifacts,
            warnings=warnings,
            structured_summary=structured,
            evidence_refs=evidence_refs,
            provider_context=provider_context,
        )

    def structured_answer(
        self,
        request: LucioAgentRequest,
        artifacts: list[LucioVisualArtifact],
        visual_summaries: list[dict[str, Any]],
        warnings: list[str],
        decision: LucioRouteDecision | None,
    ) -> str:
        route = decision.route_type if decision else "answer_directly"
        seen = ", ".join(self._safe_label(item) for item in artifacts) or "nenhum artifact"
        vision_notes = [
            str(item.get("summary") or item.get("status") or "analise visual registrada")
            for item in visual_summaries
        ]
        note = " ".join(vision_notes) if vision_notes else "Usei os metadados dos artifacts anexados como evidencia; nenhum raw foi exposto."
        warning_text = " ".join(warnings) if warnings else "Nenhum segredo evidente foi propagado para a resposta normal."
        delegation = "Sim, se a correcao exigir side effect local." if route in {"delegate_to_codex", "delegate_to_aipinho"} else "Nao neste momento."
        return (
            "O que estou vendo: ha evidencias anexadas nesta sessao "
            f"({seen}).\n"
            f"Problema provavel: {self._problem_hint(request.prompt, artifacts)}\n"
            f"Impacto: a decisao deve considerar os artifacts sem expor raw ou storage interno.\n"
            f"Causa provavel: {note}\n"
            "Correcao recomendada: revisar a superficie indicada, preservar evidence_refs e delegar somente se houver acao tecnica.\n"
            f"Risco: {'atencao a dados sensiveis no artifact.' if warnings else 'baixo, desde que o fluxo continue governado.'}\n"
            f"Proximo passo: {self._next_step(route)}\n"
            f"Deve delegar: {delegation}\n"
            f"Evidencias: {', '.join(f'artifact:{item.artifact_id}' for item in artifacts)}\n"
            f"Privacidade: {warning_text}"
        )

    def provider_context(
        self,
        artifacts: list[LucioVisualArtifact],
        visual_summaries: list[dict[str, Any]],
        warnings: list[str],
        decision: LucioRouteDecision | None,
    ) -> str:
        payload = {
            "lucio_multimodal": True,
            "route_decision": decision.model_dump() if decision else None,
            "artifacts": [item.model_dump() for item in artifacts],
            "visual_summaries": visual_summaries,
            "privacy_warnings": warnings,
            "raw_images_not_included": True,
        }
        return f"Contexto multimodal governado sanitizado:\n{redact_payload(payload)}"

    def _visual_artifact(self, session_id: str, data: dict[str, Any]) -> LucioVisualArtifact:
        artifact_id = str(data.get("artifact_id") or "")
        record = self.gateway.get_artifact(artifact_id) if artifact_id else None
        if record is not None:
            content_type = record.content_type
            filename = record.filename
            size = record.size
            source_session_id = record.session_id
            metadata = record.metadata_sanitized
            preview = self._is_visual(content_type)
        else:
            content_type = data.get("content_type")
            filename = data.get("filename")
            size = None
            source_session_id = session_id
            metadata = {}
            preview = self._is_visual(content_type)
        warnings = self._sensitivity_warnings(artifact_id, filename, content_type, metadata)
        return LucioVisualArtifact(
            artifact_id=artifact_id,
            filename=filename,
            content_type=content_type,
            size=size,
            preview_available=preview,
            source_session_id=source_session_id,
            redaction_status="sensitive_possible" if warnings else str(data.get("redaction_status") or "not_required"),
            evidence_ref=f"artifact:{artifact_id}" if artifact_id else None,
        )

    def _analyze_visual(self, artifact: LucioVisualArtifact, prompt: str) -> dict[str, Any]:
        source_ref = ImageSourceRef(
            image_id=artifact.artifact_id,
            source_type="uploaded_image",
            file_name=artifact.filename,
            mime_type=artifact.content_type,
            origin="lucio_multimodal_artifact",
            metadata={"artifact_id": artifact.artifact_id, "source_agent_id": artifact.source_agent_id},
        )
        result = self.vision.analyze(
            VisionAnalysisRequest(
                image=ImageInput(
                    source_ref=source_ref,
                    declared_purpose="lucio_multimodal_review",
                    scope="user_request",
                    mime_type=artifact.content_type,
                    file_name=artifact.filename,
                    file_size_bytes=artifact.size,
                    metadata={"artifact_id": artifact.artifact_id},
                ),
                prompt=prompt,
                purpose="ui_inspection",
            )
        )
        return {
            "vision_run_id": result.run_id,
            "status": result.status,
            "summary": result.summary,
            "trace_id": result.trace_id,
            "blocked_reasons": result.blocked_reasons,
            "warnings": result.warnings,
        }

    def _warnings(self, artifacts: list[LucioVisualArtifact]) -> list[str]:
        warnings: list[str] = []
        for item in artifacts:
            warnings.extend(self._sensitivity_warnings(item.artifact_id, item.filename, item.content_type, item.model_dump()))
        return list(dict.fromkeys(warnings))

    def _sensitivity_warnings(self, artifact_id: str | None, filename: str | None, content_type: str | None, metadata: dict[str, Any]) -> list[str]:
        payload = {"artifact_id": artifact_id, "filename": filename, "content_type": content_type, "metadata": metadata}
        if contains_secret(payload):
            return ["sensitive_possible_redacted"]
        return []

    def _redaction_status(self, artifacts: list[LucioVisualArtifact], warnings: list[str]) -> str:
        if warnings or any(item.redaction_status == "sensitive_possible" for item in artifacts):
            return "sensitive_possible"
        return "not_required"

    def _is_visual(self, content_type: str | None) -> bool:
        return str(content_type or "").lower() in VISUAL_CONTENT_TYPES

    def _safe_label(self, artifact: LucioVisualArtifact) -> str:
        filename = artifact.filename or artifact.artifact_id
        return f"{filename} ({artifact.content_type or 'tipo desconhecido'})"

    def _problem_hint(self, prompt: str, artifacts: list[LucioVisualArtifact]) -> str:
        lowered = prompt.casefold()
        if "erro" in lowered or "falha" in lowered:
            return "ha indicio de erro ou falha descrita pelo usuario."
        if "ux" in lowered or "tela" in lowered or "botao" in lowered:
            return "ha indicio de avaliacao visual de UX."
        if any(self._is_visual(item.content_type) for item in artifacts):
            return "ha um artifact visual que precisa ser interpretado com cautela."
        return "ha evidencia anexada para revisao estrategica."

    def _next_step(self, route: str | None) -> str:
        if route == "ask_clarification":
            return "pedir uma imagem melhor ou esclarecimento antes de concluir."
        if route == "delegate_to_codex":
            return "delegar plano tecnico ao Codex por contrato governado."
        if route == "delegate_to_aipinho":
            return "delegar diagnostico local a AIpinho por contrato governado."
        return "responder com diagnostico e plano sem executar side effects locais."
