from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.schemas.chat.manual_chat_inference_response import ManualChatInferenceResponse
from aipinho.schemas.models.generation_config import GenerationConfig
from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.services.chat.chat_inference_trace_service import ChatInferenceTraceService
from aipinho.services.chat.chat_manual_inference_audit_service import ChatManualInferenceAuditService
from aipinho.services.chat.chat_model_fallback_service import ChatModelFallbackService
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService
from aipinho.services.chat.chat_model_response_service import ChatModelResponseService
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService
from aipinho.services.session.session_service import SessionService


class ChatManualInferenceService:
    def __init__(
        self,
        policy_service: ChatModelPolicyService | None = None,
        prompt_assembly_service: PromptAssemblyService | None = None,
        model_invocation_service: ModelInvocationService | None = None,
        response_service: ChatModelResponseService | None = None,
        fallback_service: ChatModelFallbackService | None = None,
        trace_service: ChatInferenceTraceService | None = None,
        audit_service: ChatManualInferenceAuditService | None = None,
        session_service: SessionService | None = None,
    ) -> None:
        self.policy_service = policy_service or ChatModelPolicyService()
        self.prompt_assembly_service = prompt_assembly_service or PromptAssemblyService()
        self.model_invocation_service = model_invocation_service or ModelInvocationService()
        self.response_service = response_service or ChatModelResponseService()
        self.fallback_service = fallback_service or ChatModelFallbackService()
        self.trace_service = trace_service or ChatInferenceTraceService()
        self.audit_service = audit_service or ChatManualInferenceAuditService()
        self.session_service = session_service or SessionService()

    def preview(self, request: ManualChatInferenceRequest) -> ManualChatInferenceResponse:
        trace = [self.trace_service.item("request", "ok", "manual_chat_preview_requested")]
        validation = self.policy_service.validate_request(request)
        preview = self._build_prompt_preview(request, validation)
        gate_decision = dict(validation.get("manual_gate_decision", {}))
        prompt_budget = preview.assembly.budget.model_dump()
        warnings = list(dict.fromkeys([*validation.get("warnings", []), *preview.assembly.warnings]))
        if not validation.get("allowed", False):
            fallback = self.fallback_service.build(",".join(validation.get("blocked_reasons", [])), status="preview")
            response = ManualChatInferenceResponse(
                session_id=request.session_id,
                status="blocked",
                message=fallback.safe_message or "Preview bloqueado.",
                process_started=False,
                real_inference=False,
                fallback=fallback,
                gate_decision=gate_decision,
                prompt_budget=prompt_budget,
                prompt_preview=self._prompt_preview_summary(preview, process_started=False),
                warnings=list(dict.fromkeys([*warnings, *validation.get("blocked_reasons", [])])),
                trace=self.trace_service.visible([*trace, self.trace_service.item("policy", "blocked", ",".join(validation.get("blocked_reasons", [])))], include=request.include_trace),
            )
            self.audit_service.record(event_type="manual_chat_preview_blocked", request=request, response=response, gate_decision=gate_decision, warnings=response.warnings)
            return response
        model_preview: dict[str, Any] = {}
        try:
            model_preview = self.model_invocation_service.inference_runtime.invoke_preview(self._model_request_from_preview(request, preview, validation))
            gate_decision = model_preview.get("gate_decision", gate_decision) if isinstance(model_preview.get("gate_decision"), dict) else gate_decision
        except Exception as exc:
            warnings.append(str(exc))
            trace.append(self.trace_service.item("model_preview", "degraded", str(exc)))
        response = ManualChatInferenceResponse(
            response_id=f"manual_chat_preview_{uuid4().hex}",
            session_id=request.session_id,
            status="preview",
            message="Preview de inferencia local manual pronto. Nenhum processo de modelo foi iniciado.",
            process_started=False,
            real_inference=False,
            gate_decision=gate_decision,
            prompt_budget=prompt_budget,
            prompt_preview={**self._prompt_preview_summary(preview, process_started=False), "model_preview": model_preview},
            warnings=list(dict.fromkeys(warnings)),
            trace=self.trace_service.visible([*trace, self.trace_service.item("preview", "ok", "process_not_started")], include=request.include_trace),
        )
        self.audit_service.record(event_type="manual_chat_preview", request=request, response=response, gate_decision=gate_decision, warnings=response.warnings)
        return response

    def run(self, request: ManualChatInferenceRequest) -> ManualChatInferenceResponse:
        trace = [self.trace_service.item("request", "ok", "manual_chat_inference_requested")]
        validation = self.policy_service.validate_request(request)
        preview = self._build_prompt_preview(request, validation)
        gate_decision = dict(validation.get("manual_gate_decision", {}))
        warnings = list(dict.fromkeys([*validation.get("warnings", []), *preview.assembly.warnings]))
        if not validation.get("allowed", False):
            fallback = self.fallback_service.build(",".join(validation.get("blocked_reasons", [])), status="blocked")
            response = ManualChatInferenceResponse(
                session_id=request.session_id,
                status="blocked",
                message=fallback.safe_message or "Inferencia manual bloqueada.",
                process_started=False,
                real_inference=False,
                fallback=fallback,
                gate_decision=gate_decision,
                prompt_budget=preview.assembly.budget.model_dump(),
                prompt_preview=self._prompt_preview_summary(preview, process_started=False),
                warnings=list(dict.fromkeys([*warnings, *validation.get("blocked_reasons", [])])),
                trace=self.trace_service.visible([*trace, self.trace_service.item("policy", "blocked", ",".join(validation.get("blocked_reasons", [])))], include=request.include_trace),
            )
            self.audit_service.record(event_type="manual_chat_inference_blocked", request=request, response=response, gate_decision=gate_decision, warnings=response.warnings)
            return response
        try:
            model_request = self._model_request_from_preview(request, preview, validation)
            model_response = self.model_invocation_service.invoke(model_request)
            converted = self.response_service.convert(model_response, profile_id=request.profile_id)
            status = converted["status"]
            if model_response.finish_reason == "timeout":
                status = "timeout"
            response = ManualChatInferenceResponse(
                session_id=request.session_id,
                status=status,
                message=converted["message"],
                process_started=bool(model_response.real_inference),
                real_inference=bool(model_response.real_inference),
                model=converted["model"],
                evaluation=converted["evaluation"],
                fallback=converted["fallback"],
                gate_decision=model_response.trace[0] if model_response.trace else gate_decision,
                prompt_budget=preview.assembly.budget.model_dump(),
                prompt_preview=self._prompt_preview_summary(preview, process_started=bool(model_response.real_inference)),
                warnings=list(dict.fromkeys([*warnings, *converted["warnings"]])),
                trace=self.trace_service.visible([*trace, *[self.trace_service.item(str(item.get("stage", "model")), str(item.get("status", "ok")), str(item.get("reason", "")), data={k: v for k, v in item.items() if k not in {"stage", "status", "reason"}}) for item in model_response.trace]], include=request.include_trace),
            )
        except Exception as exc:
            fallback = self.fallback_service.build(str(exc), status="unavailable")
            response = ManualChatInferenceResponse(
                session_id=request.session_id,
                status="error",
                message=fallback.safe_message or "Inferencia manual indisponivel.",
                process_started=False,
                real_inference=False,
                fallback=fallback,
                gate_decision=gate_decision,
                prompt_budget=preview.assembly.budget.model_dump(),
                prompt_preview=self._prompt_preview_summary(preview, process_started=False),
                warnings=list(dict.fromkeys([*warnings, str(exc)])),
                trace=self.trace_service.visible([*trace, self.trace_service.item("manual_chat_service", "error", str(exc))], include=request.include_trace),
            )
        self.audit_service.record(event_type="manual_chat_inference", request=request, response=response, gate_decision=gate_decision, warnings=response.warnings)
        return response

    def _build_prompt_preview(self, request: ManualChatInferenceRequest, validation: dict[str, Any]):
        profile = validation.get("profile")
        output_contract_type = getattr(profile, "output_contract_type", None) or str(self.policy_service.manual_chat.get("output_contract_type", "chat_response"))
        return self.prompt_assembly_service.preview(
            PromptAssemblyRequest(
                purpose="chat",
                role_id="speaker",
                user_message=request.message,
                session_context={"session_id": request.session_id, "surface": getattr(request.context, "surface", "api") if request.context else "api"},
                output_contract_type=output_contract_type,
                model_id=request.model_id,
                include_trace=request.include_trace,
            )
        )

    def _model_request_from_preview(self, request: ManualChatInferenceRequest, preview: Any, validation: dict[str, Any]):
        profile = validation.get("profile")
        model_request = preview.model_request.model_copy(deep=True)
        model_request.model_id = request.model_id
        model_request.provider_id = request.provider_id
        model_request.generation_config = GenerationConfig(
            temperature=float(getattr(profile, "temperature", 0.0) if profile else 0.0),
            top_p=float(getattr(profile, "top_p", 1.0) if profile else 1.0),
            max_tokens=int(getattr(profile, "max_output_tokens", 256) if profile else 256),
        )
        safety = dict(model_request.safety_envelope or {})
        safety["envelope_id"] = getattr(profile, "safety_envelope_id", None) or str(self.policy_service.manual_chat.get("safety_envelope_id", "local_manual_inference"))
        safety["real_inference"] = True
        safety["rules"] = list(dict.fromkeys([*(safety.get("rules", []) or []), "Nao executar tools.", "Nao escrever arquivos.", "Nao usar rede.", "Nao usar RAG ou memoria.", "Nao aplicar patch."]))
        model_request.safety_envelope = safety
        model_request.metadata = {
            **model_request.metadata,
            "purpose": "chat",
            "role_id": "speaker",
            "manual_mode": True,
            "chat_manual_inference": True,
            "allow_real_inference": request.allow_real_inference,
            "operator_confirmed": request.operator_confirmed,
            "profile_id": request.profile_id,
            "timeout_seconds": int(getattr(profile, "timeout_seconds", 45) if profile else 45),
            "ctx_size": int(getattr(profile, "ctx_size", 2048) if profile else 2048),
            "include_evaluation_trace": request.include_trace,
            "tool_calling_enabled": False,
            "write_enabled": False,
            "patch_enabled": False,
            "shell_enabled": False,
            "rag_enabled": False,
            "memory_write_enabled": False,
            "network_enabled": False,
        }
        return model_request

    def _prompt_preview_summary(self, preview: Any, *, process_started: bool) -> dict[str, Any]:
        return {
            "assembly_id": preview.assembly.assembly_id,
            "invokes_model": False,
            "side_effects": False,
            "process_started": process_started,
            "message_count": len(preview.assembly.messages),
            "budget": preview.assembly.budget.model_dump(),
            "output_contract": preview.assembly.output_contract.model_dump(),
            "safety_envelope": preview.assembly.safety_envelope.model_dump(),
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "chat_manual_inference", "policy": self.policy_service.status(), "response": self.response_service.status(), "audit": self.audit_service.status()}
