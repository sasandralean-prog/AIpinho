from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import (
    AgentEventCreateRequest,
    AgentMessageCreateRequest,
    AgentRunCreateRequest,
    AgentRunUpdateRequest,
    AgentSessionCreateRequest,
    AgentSessionUpdateRequest,
)
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.memory import MemoryCandidateCreateRequest, MemoryContextLoadRequest
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.lucio_agent import LucioAgentRequest, LucioAgentResponse, LucioRouteDecision
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner
from aipinho.services.agents.agent_memory_gateway_service import AgentMemoryGatewayService
from aipinho.services.agents.agent_request_enrichment_service import AgentRequestEnrichmentService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.events.event_core import redact_payload
from aipinho.services.lucio_agent.lucio_agent_config_service import LucioAgentConfigService
from aipinho.services.lucio_agent.lucio_multimodal_service import LucioMultimodalService
from aipinho.services.lucio_agent.lucio_openai_client import OpenAILucioClient
from aipinho.services.lucio_agent.lucio_route_policy_service import LucioRoutePolicyService
from aipinho.services.lucio_agent.lucio_safe_fallback_service import LucioSafeFallbackService


class LucioAgentService:
    agent_id = "lucio"

    def __init__(
        self,
        *,
        config_service: LucioAgentConfigService | None = None,
        route_policy: LucioRoutePolicyService | None = None,
        client: Any | None = None,
        kernel: AgentSessionKernelService | None = None,
        delegation_service: AgentDelegationService | None = None,
        memory_gateway: AgentMemoryGatewayService | None = None,
        local_action_planner: AgentLocalActionPlanner | None = None,
        multimodal_service: LucioMultimodalService | None = None,
        request_enrichment: AgentRequestEnrichmentService | None = None,
        safe_fallback: LucioSafeFallbackService | None = None,
    ) -> None:
        self.config_service = config_service or LucioAgentConfigService()
        self.route_policy = route_policy or LucioRoutePolicyService(self.config_service.policy_path)
        self.client = client
        self.kernel = kernel or AgentSessionKernelService()
        self.delegation_service = delegation_service or AgentDelegationService(kernel=self.kernel)
        self.memory_gateway = memory_gateway or AgentMemoryGatewayService(kernel=self.kernel)
        self.local_action_planner = local_action_planner or AgentLocalActionPlanner(AgentToolGatewayService(kernel=self.kernel))
        self.multimodal_service = multimodal_service or LucioMultimodalService()
        self.request_enrichment = request_enrichment or AgentRequestEnrichmentService()
        self.safe_fallback = safe_fallback or LucioSafeFallbackService()
        self._last_provider_error: str | None = None
        self._last_provider_error_at: str | None = None

    def health(self) -> dict[str, object]:
        status = self.config_service.status(
            last_error_sanitized=self._last_provider_error,
            last_provider_error_at=self._last_provider_error_at,
        )
        health = "ok" if status.enabled and status.provider_configured else "degraded"
        if not status.enabled:
            health = "disabled_by_config"
        return {
            "status": health,
            "agent_id": self.agent_id,
            "provider": status.provider,
            "config": status.model_dump(),
        }

    def create_session(self, title: str = "Lucio") -> Any:
        runtime = self.config_service.runtime()
        if not runtime.allow_new_sessions:
            raise PermissionError("agent_disabled")
        return self.kernel.create_session(
            self.agent_id,
            AgentSessionCreateRequest(
                title=title,
                metadata_sanitized={
                    "provider": runtime.provider,
                    "history_source": "agent_session_kernel",
                },
            ),
        )

    def sessions(self) -> list[Any]:
        return self.kernel.list_sessions(self.agent_id, include_compat=False)

    def get_session(self, session_id: str) -> Any | None:
        return self.kernel.get_session(self.agent_id, session_id, include_compat=False)

    def rename_session(self, session_id: str, title: str) -> Any | None:
        return self.kernel.update_session(
            self.agent_id,
            session_id,
            AgentSessionUpdateRequest(title=title),
        )

    def delete_session(self, session_id: str) -> Any | None:
        return self.kernel.delete_session(self.agent_id, session_id)

    def messages(self, session_id: str) -> list[Any]:
        if self.get_session(session_id) is None:
            raise FileNotFoundError(session_id)
        return self.kernel.list_messages(self.agent_id, session_id, include_raw_ref=False)

    def route_preview(self, request: LucioAgentRequest) -> LucioRouteDecision:
        return self.route_policy.decide(request)

    def send(self, request: LucioAgentRequest) -> LucioAgentResponse:
        config = self.config_service.runtime()
        if not config.enabled:
            return self._disabled_response_model(request, config.default_model)
        if self.get_session(request.session_id) is None:
            raise FileNotFoundError(request.session_id)
        request = self._enrich_request(request)

        model = request.model or config.default_model
        prompt = request.prompt[: config.max_prompt_chars]
        request = request.model_copy(update={"prompt": prompt})
        decision = self.route_policy.decide(request)
        multimodal = self.multimodal_service.build_context(request, decision)

        self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="user",
                content_sanitized=prompt,
                metadata_sanitized={
                    "operation_type": request.operation_type,
                    "artifact_count": len(request.artifacts),
                    "multimodal": bool(multimodal),
                },
            ),
        )
        run = self.kernel.create_run(
            self.agent_id,
            request.session_id,
            AgentRunCreateRequest(
                operation_type=request.operation_type,
                status="running",
                workspace_id=request.workspace_id,
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={
                    "provider": config.provider,
                    "model": model,
                    "execution_mode": request.execution_mode or config.default_execution_mode,
                    "route": decision.route,
                    "route_type": decision.route_type,
                    "artifact_count": len(request.artifacts),
                    "input_modalities": decision.input_modalities,
                },
            ),
        )
        self._event(
            run.run_id,
            "lucio_request_received",
            "Lucio recebeu o pedido e iniciou a avaliacao estrategica.",
            {
                "operation_type": request.operation_type,
                "artifact_count": len(request.artifacts),
            },
        )
        self._event(
            run.run_id,
            "lucio_route_decided",
            self._route_summary(decision),
            decision.model_dump(),
        )
        if multimodal is not None:
            self._event(
                run.run_id,
                "lucio_multimodal_message_created",
                "Lucio associou artifacts multimodais governados a mensagem.",
                {
                    "message_id": multimodal.message.message_id,
                    "artifact_refs": multimodal.message.artifact_refs,
                    "content_types": multimodal.message.content_types,
                    "redaction_status": multimodal.message.redaction_status,
                    "raw_images_not_included": True,
                },
                status="received",
            )
            self._event(
                run.run_id,
                "lucio_visual_analysis_available",
                "Lucio preparou uma analise visual estruturada e sanitizada.",
                {
                    "visual_artifacts": [item.model_dump() for item in multimodal.visual_artifacts],
                    "evidence_refs": multimodal.evidence_refs,
                    "warnings": multimodal.warnings,
                },
                status="completed",
            )

        memory_context, memory_refs, memory_warnings = self._load_memory(run.run_id, request)

        if decision.route in {"ask_clarification", "request_better_image", "request_missing_artifact"}:
            response = self._clarification_response(
                request,
                run.run_id,
                model,
                decision,
                memory_refs,
                memory_warnings,
                multimodal,
            )
            self._create_memory_candidate(response)
            return response

        if decision.route in {"delegate_codex", "delegate_aipinho"}:
            if not config.use_delegation:
                return self._fail(
                    request,
                    run.run_id,
                    model,
                    decision,
                    "lucio_delegation_disabled",
                    "O pedido exige execucao delegada, mas a delegacao esta desabilitada.",
                    memory_refs,
                    memory_warnings,
                    status="blocked",
                )
            response = self._delegate(request, run.run_id, model, decision, memory_refs, memory_warnings, multimodal)
            self._create_memory_candidate(response)
            return response

        client = self.client or OpenAILucioClient(
            config.api_key,
            base_url=config.base_url,
            project=config.project,
            organization=config.organization,
        )
        self._event(
            run.run_id,
            "lucio_provider_request_started",
            "Lucio iniciou uma resposta estrategica direta pelo provider configurado.",
            {
                "provider": "openai",
                "model": model,
                "provider_configured": bool(config.api_key),
                "auth_present": bool(config.api_key),
                "request_started": True,
            },
        )
        result = client.respond(
            prompt=prompt,
            model=model,
            timeout_seconds=config.timeout_seconds,
            max_output_chars=request.max_output_chars or config.max_output_chars,
            context_sanitized=self._provider_context(memory_context, request, multimodal.provider_context if multimodal else ""),
        )
        if result.status != "completed":
            error_code = result.error_code or "openai_provider_error"
            self._record_provider_error(error_code)
            self._event(
                run.run_id,
                "lucio_provider_request_failed",
                self._provider_failure_message(error_code),
                {
                    "provider": "openai",
                    "model": model,
                    "provider_error": error_code,
                    "request_failed": True,
                    "model_invoked": False,
                    "provider_invocation_failed": True,
                    "local_execution_started": False,
                    "tool_invoked": False,
                    "delegation_started": False,
                },
                severity="warning",
                status="failed",
            )
            fallback_decision = self.safe_fallback.classify(
                prompt=prompt,
                requires_local_execution=decision.requires_local_execution,
                requested_capabilities=request.requested_capabilities,
            )
            if fallback_decision.allowed:
                response = self._safe_local_fallback_response(
                    request,
                    run.run_id,
                    model,
                    decision,
                    error_code,
                    fallback_decision.category,
                    fallback_decision.response_text,
                    memory_refs,
                    [*memory_warnings, f"provider_warning:{error_code}", "fallback_used:local_safe_chat"],
                    fallback_decision.reasons,
                )
                self._create_memory_candidate(response)
                return response
            return self._provider_unavailable_response(
                request,
                run.run_id,
                model,
                decision,
                error_code,
                fallback_decision.category,
                memory_refs,
                [*memory_warnings, f"provider_warning:{error_code}", "fallback_not_allowed"],
                fallback_decision.reasons,
            )

        response_text = result.text
        if multimodal is not None:
            response_text = f"{multimodal.structured_summary}\n\nAnalise estrategica:\n{result.text}"
            response_text = response_text[: (request.max_output_chars or config.max_output_chars)]
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="final_answer",
                content_sanitized=response_text,
                run_id=run.run_id,
                artifact_ids=[artifact.artifact_id for artifact in request.artifacts],
                metadata_sanitized={
                    "provider": "openai",
                    "model": result.model,
                    "route": decision.route,
                    "route_type": decision.route_type,
                    "multimodal_message_id": multimodal.message.message_id if multimodal else None,
                },
            ),
        )
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status="completed",
                final_message_id=assistant.message_id,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
                metadata_sanitized={
                    "provider": "openai",
                    "model": result.model,
                    "route": decision.route,
                    "route_type": decision.route_type,
                    "multimodal_message_id": multimodal.message.message_id if multimodal else None,
                },
            ),
        )
        self._event(
            run.run_id,
            "lucio_response_completed",
            "Lucio concluiu a resposta estrategica sem executar ferramentas locais.",
            {"provider": "openai", "model": result.model},
            status="completed",
        )
        response = LucioAgentResponse(
            session_id=request.session_id,
            run_id=run.run_id,
            status="completed",
            model=result.model,
            text=response_text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            multimodal_message=multimodal.message if multimodal else None,
            visual_artifacts=multimodal.visual_artifacts if multimodal else [],
            artifact_ids=[artifact.artifact_id for artifact in request.artifacts],
            evidence_refs=[f"run:{run.run_id}", *[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts]],
            memory_refs_used=memory_refs,
            warnings=[*memory_warnings, *(multimodal.warnings if multimodal else [])],
        )
        self._create_memory_candidate(response)
        return response

    def _enrich_request(self, request: LucioAgentRequest) -> LucioAgentRequest:
        enrichment = self.request_enrichment.enrich(
            prompt=request.prompt,
            operation_type=request.operation_type,
            requested_capabilities=request.requested_capabilities,
            workspace_context=request.workspace_id,
            target_paths=request.target_paths,
        )
        return request.model_copy(
            update={
                "operation_type": enrichment.operation_type or request.operation_type,
                "requested_capabilities": enrichment.requested_capabilities,
                "workspace_id": enrichment.workspace_context,
                "target_paths": enrichment.target_paths,
                "metadata_sanitized": {
                    **request.metadata_sanitized,
                    "request_enrichment_evidence": enrichment.evidence,
                },
            }
        )

    def _try_local_create_file(
        self,
        request: LucioAgentRequest,
        run_id: str,
        model: str,
        decision: LucioRouteDecision,
        memory_refs: list[str],
        memory_warnings: list[str],
    ) -> LucioAgentResponse | None:
        workspace_context = request.workspace_id or (request.target_paths[0] if request.target_paths else None)
        result = self.local_action_planner.run_explicit_create_file(
            agent_id=self.agent_id,
            run_id=run_id,
            prompt=request.prompt,
            workspace_context=workspace_context,
            requested_capabilities=request.requested_capabilities,
            execution_mode=request.execution_mode or self.config_service.runtime().default_execution_mode,
            metadata_sanitized={"source": "lucio_local_action_planner", "route": decision.route},
        )
        if result is None:
            return None
        status = "completed" if result.status == "succeeded" else ("blocked" if result.status in {"blocked", "approval_required"} else "failed")
        text = (
            "Executei a ação local pelo Tool Gateway governado.\n"
            f"Ferramenta: {result.tool_invocation.tool_name}\n"
            f"Status: {result.status}\n"
            f"Evidência: {result.tool_invocation.output_summary_sanitized or result.tool_invocation.tool_invocation_id}"
        )
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="final_answer" if status == "completed" else "tool_status",
                content_sanitized=text,
                run_id=run_id,
                metadata_sanitized={
                    "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                    "tool_name": result.tool_invocation.tool_name,
                    "tool_status": result.status,
                    "route": decision.route,
                },
            ),
        )
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status=status,
                final_message_id=assistant.message_id,
                error_code=result.tool_invocation.error_code,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
                metadata_sanitized={
                    "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                    "tool_name": result.tool_invocation.tool_name,
                    "tool_status": result.status,
                    "route": decision.route,
                },
            ),
        )
        self._event(
            run_id,
            "lucio_local_tool_completed" if result.status == "succeeded" else "lucio_local_tool_not_completed",
            "Lucio acionou uma ferramenta local governada via Tool Gateway.",
            {
                "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                "tool_name": result.tool_invocation.tool_name,
                "status": result.status,
                "block_reason_code": result.tool_invocation.block_reason_code,
            },
            severity="info" if result.status == "succeeded" else "warning",
            status=result.status,
        )
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id=run_id,
            status=status,
            model=model,
            text=text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            evidence_refs=[f"run:{run_id}", f"tool:{result.tool_invocation.tool_invocation_id}"],
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
            error_code=result.tool_invocation.error_code,
        )

    def cancel_run(self, run_id: str) -> dict[str, object]:
        run = self.kernel.get_run(run_id)
        if run is None or run.agent_id != self.agent_id:
            raise FileNotFoundError(run_id)
        delegation_id = str(run.metadata_sanitized.get("delegation_id") or "")
        if delegation_id:
            try:
                self.delegation_service.cancel(delegation_id)
            except FileNotFoundError:
                pass
        updated = self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(status="cancelled", metadata_sanitized={"cancelled_by": "user"}),
        )
        self._event(run_id, "lucio_run_cancelled", "Run do Lucio cancelado de forma controlada.", {}, status="cancelled")
        return {"status": "cancelled", "run": updated.model_dump() if updated else None}

    def _delegate(
        self,
        request: LucioAgentRequest,
        run_id: str,
        model: str,
        decision: LucioRouteDecision,
        memory_refs: list[str],
        memory_warnings: list[str],
        multimodal=None,
    ) -> LucioAgentResponse:
        target = decision.target_agent_id
        if target not in {"codex", "aipinho"}:
            return self._fail(
                request,
                run_id,
                model,
                decision,
                "lucio_route_target_invalid",
                "A politica produziu um destino de delegacao invalido.",
                memory_refs,
                memory_warnings,
                status="blocked",
            )
        try:
            delegation = self.delegation_service.create_delegation(
                self.agent_id,
                run_id,
                DelegationCreateRequest(
                    target_agent_id=target,
                    user_goal=request.prompt,
                    requested_operation=decision.delegated_operation or request.operation_type,
                    operation_type=decision.delegated_operation or request.operation_type,
                    workspace_id=request.workspace_id,
                    capabilities_requested=request.requested_capabilities,
                    constraints={
                        "target_path_count": len(request.target_paths),
                        "artifact_ids": [artifact.artifact_id for artifact in request.artifacts],
                        "artifact_refs": [f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
                        "screenshot_refs": [artifact.artifact_id for artifact in request.artifacts if str(artifact.content_type or "").lower().startswith("image/")],
                        "visual_context_summary": multimodal.structured_summary if multimodal else "",
                        "observed_problem": decision.detected_intent or request.operation_type,
                        "requested_change": request.prompt,
                        "validation_expectation": "Delegated work must return evidence_refs and validation status when side effects occur.",
                        "local_tools_must_use_gateway": True,
                    },
                    expected_outputs=["human_summary", "event_trace", "validation_evidence"],
                    memory_refs=memory_refs,
                    risk_level=self._risk_level(request),
                    execution_mode=request.execution_mode or self.config_service.runtime().default_execution_mode,
                    metadata_sanitized={
                        "source_agent": self.agent_id,
                        "route": decision.route,
                        "route_type": decision.route_type,
                        "provider": "openai",
                        "multimodal_message_id": multimodal.message.message_id if multimodal else None,
                    },
                ),
            )
        except Exception as exc:
            return self._fail(
                request,
                run_id,
                model,
                decision,
                f"lucio_delegation_failed:{type(exc).__name__}",
                "A delegacao governada falhou antes da execucao do agente filho.",
                memory_refs,
                memory_warnings,
                status="failed",
            )

        status_map = {
            "running": "delegation_running",
            "approval_required": "pending_approval",
            "blocked": "blocked",
            "failed": "failed",
        }
        status = status_map.get(delegation.status, delegation.status)
        summary = delegation.result.summary if delegation.result else "Delegacao criada; aguardando eventos do agente executor."
        text = (
            f"Encaminhei o trabalho para {target} pelo fluxo governado. "
            f"Status atual: {delegation.status}. {summary}"
        )
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="delegation_notice",
                content_sanitized=text,
                run_id=run_id,
                metadata_sanitized={
                    "delegation_id": delegation.delegation.delegation_id,
                    "child_run_id": delegation.delegation.child_run_id,
                    "target_agent_id": target,
                },
            ),
        )
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status=status,
                final_message_id=assistant.message_id,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
                metadata_sanitized={
                    "delegation_id": delegation.delegation.delegation_id,
                    "child_run_id": delegation.delegation.child_run_id,
                    "target_agent_id": target,
                    "route": decision.route,
                },
            ),
        )
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id=run_id,
            status=status,
            model=model,
            text=text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            multimodal_message=multimodal.message if multimodal else None,
            visual_artifacts=multimodal.visual_artifacts if multimodal else [],
            delegation_id=delegation.delegation.delegation_id,
            child_run_id=delegation.delegation.child_run_id,
            artifact_ids=[artifact.artifact_id for artifact in request.artifacts],
            evidence_refs=[
                f"run:{run_id}",
                f"delegation:{delegation.delegation.delegation_id}",
                *([f"run:{delegation.delegation.child_run_id}"] if delegation.delegation.child_run_id else []),
                *[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
            ],
            memory_refs_used=memory_refs,
            warnings=[*memory_warnings, *(multimodal.warnings if multimodal else [])],
        )

    def _clarification_response(
        self,
        request: LucioAgentRequest,
        run_id: str,
        model: str,
        decision: LucioRouteDecision,
        memory_refs: list[str],
        memory_warnings: list[str],
        multimodal=None,
    ) -> LucioAgentResponse:
        text = decision.clarification_question or "Preciso de mais contexto antes de analisar esse artifact com seguranca."
        if multimodal is not None:
            text = f"{text}\n\nEvidencias recebidas: {', '.join(multimodal.evidence_refs)}"
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="final_answer",
                content_sanitized=text,
                run_id=run_id,
                artifact_ids=[artifact.artifact_id for artifact in request.artifacts],
                metadata_sanitized={
                    "route": decision.route,
                    "route_type": decision.route_type,
                    "requires_clarification": True,
                },
            ),
        )
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status="completed_with_warnings",
                final_message_id=assistant.message_id,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
                metadata_sanitized={
                    "route": decision.route,
                    "route_type": decision.route_type,
                    "requires_clarification": True,
                },
            ),
        )
        self._event(
            run_id,
            "lucio_clarification_requested",
            text,
            {"route": decision.route, "clarification_question": decision.clarification_question},
            severity="warning",
            status="completed_with_warnings",
        )
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id=run_id,
            status="completed_with_warnings",
            model=model,
            text=text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            multimodal_message=multimodal.message if multimodal else None,
            visual_artifacts=multimodal.visual_artifacts if multimodal else [],
            artifact_ids=[artifact.artifact_id for artifact in request.artifacts],
            evidence_refs=[f"run:{run_id}", *[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts]],
            memory_refs_used=memory_refs,
            warnings=[*memory_warnings, *(multimodal.warnings if multimodal else [])],
        )

    def _safe_local_fallback_response(
        self,
        request: LucioAgentRequest,
        run_id: str,
        model: str,
        decision: LucioRouteDecision,
        provider_error: str,
        fallback_category: str,
        text: str,
        memory_refs: list[str],
        memory_warnings: list[str],
        fallback_reasons: list[str],
    ) -> LucioAgentResponse:
        metadata = {
            "route": decision.route,
            "route_type": decision.route_type,
            "provider": "openai",
            "model": model,
            "provider_error": provider_error,
            "fallback_used": True,
            "fallback_type": "local_safe_chat",
            "fallback_category": fallback_category,
            "fallback_reasons": fallback_reasons,
            "model_invoked": False,
            "provider_invocation_failed": True,
            "local_execution_started": False,
            "tool_invoked": False,
            "delegation_started": False,
            "final_status": "completed_with_warnings",
        }
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="final_answer",
                content_sanitized=text,
                run_id=run_id,
                metadata_sanitized=metadata,
            ),
        )
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status="completed_with_warnings",
                final_message_id=assistant.message_id,
                error_code=provider_error,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
                metadata_sanitized=metadata,
            ),
        )
        self._event(
            run_id,
            "lucio_safe_local_fallback_used",
            "Lucio usou fallback local seguro porque o provider falhou e a pergunta era simples.",
            metadata,
            severity="warning",
            status="completed_with_warnings",
        )
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id=run_id,
            status="completed_with_warnings",
            model=model,
            text=text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            evidence_refs=[f"run:{run_id}"],
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
            error_code=provider_error,
        )

    def _provider_unavailable_response(
        self,
        request: LucioAgentRequest,
        run_id: str,
        model: str,
        decision: LucioRouteDecision,
        provider_error: str,
        fallback_category: str,
        memory_refs: list[str],
        memory_warnings: list[str],
        fallback_reasons: list[str],
    ) -> LucioAgentResponse:
        text = (
            "O provider configurado recusou ou falhou antes de gerar uma resposta. "
            "Nao vou inventar conteudo sem o modelo. Revise a credencial ou selecione outro provider. "
            "Nenhuma acao local foi executada."
        )
        metadata = {
            "route": decision.route,
            "route_type": decision.route_type,
            "provider": "openai",
            "model": model,
            "provider_error": provider_error,
            "fallback_used": False,
            "fallback_type": None,
            "fallback_category": fallback_category,
            "fallback_reasons": fallback_reasons,
            "status": "provider_unavailable",
            "reason_code": provider_error,
            "model_invoked": False,
            "provider_invocation_failed": True,
            "local_execution_started": False,
            "tool_invoked": False,
            "delegation_started": False,
            "safe_to_retry": True,
            "final_status": "completed_with_warnings",
        }
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="final_answer",
                content_sanitized=text,
                run_id=run_id,
                metadata_sanitized=metadata,
            ),
        )
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status="completed_with_warnings",
                final_message_id=assistant.message_id,
                error_code=provider_error,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
                metadata_sanitized=metadata,
            ),
        )
        self._event(
            run_id,
            "lucio_provider_unavailable",
            text,
            metadata,
            severity="warning",
            status="provider_unavailable",
        )
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id=run_id,
            status="completed_with_warnings",
            model=model,
            text=text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            evidence_refs=[f"run:{run_id}"],
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
            error_code=provider_error,
        )

    def _record_provider_error(self, error_code: str) -> None:
        self._last_provider_error = str(redact_payload(error_code))
        self._last_provider_error_at = utc_now_iso()

    def disabled_payload(self, *, session_id: str | None = None) -> dict[str, object]:
        status = self.config_service.status().model_dump()
        if session_id and self.get_session(session_id) is not None:
            run = self.kernel.create_run(
                self.agent_id,
                session_id,
                AgentRunCreateRequest(
                    operation_type="lucio_disabled_request",
                    status="blocked",
                    error_code="agent_disabled",
                    metadata_sanitized={
                        "provider": "disabled",
                        "reason_code": "agent_disabled",
                        "local_execution_started": False,
                        "tool_invoked": False,
                        "delegation_started": False,
                    },
                ),
            )
            self._event(
                run.run_id,
                "lucio_disabled_request_received",
                "Lucio esta desativado nesta instalacao.",
                {
                    "reason_code": "agent_disabled",
                    "provider": "disabled",
                    "local_execution_started": False,
                    "tool_invoked": False,
                    "delegation_started": False,
                },
                status="blocked",
                severity="warning",
            )
        return {
            "status": "blocked",
            "reason_code": "agent_disabled",
            "agent_id": self.agent_id,
            "user_message": "Lucio esta desativado nesta instalacao. Use Gemini para conversa textual ou AIpinho para execucao local.",
            "provider": "disabled",
            "local_execution_started": False,
            "tool_invoked": False,
            "delegation_started": False,
            "safe_to_retry": False,
            "config": status,
        }

    def _disabled_response_model(self, request: LucioAgentRequest, model: str) -> LucioAgentResponse:
        decision = LucioRouteDecision(
            route="blocked",
            route_type="block",
            confidence="high",
            reasons=["agent_disabled", "openai_provider_disabled_by_config"],
            reason_sanitized="Lucio esta desativado nesta instalacao.",
            requested_capabilities=request.requested_capabilities,
            required_capabilities=[],
            expected_outputs=[],
            detected_intent=request.operation_type,
            input_modalities=["text"],
            risk_level="low",
            requires_local_execution=False,
        )
        payload = self.disabled_payload(session_id=request.session_id)
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id="lucio_disabled_no_run",
            status="blocked",
            provider="disabled",
            model=model,
            text=str(payload["user_message"]),
            public_reasoning_summary="Lucio esta desativado por configuracao e nao acionou provider externo.",
            route_decision=decision,
            warnings=["agent_disabled"],
            error_code="agent_disabled",
            external_provider_notice=False,
            raw_default_visible=False,
        )

    @staticmethod
    def _provider_failure_message(error_code: str) -> str:
        messages = {
            "openai_api_key_missing": (
                "O provider externo nao esta configurado neste backend. "
                "Nenhuma acao local foi executada."
            ),
            "openai_sdk_missing": (
                "O cliente do provider externo nao esta instalado no backend. "
                "Nenhuma acao local foi executada."
            ),
            "openai_timeout": (
                "O provider externo excedeu o tempo limite. "
                "A solicitacao pode ser tentada novamente; nenhuma acao local foi executada."
            ),
            "openai_auth_error": (
                "O provider externo recusou a autenticacao configurada. "
                "Revise a credencial no backend; nenhuma acao local foi executada."
            ),
            "openai_rate_limited": (
                "O provider externo limitou temporariamente as requisicoes. "
                "Tente novamente mais tarde; nenhuma acao local foi executada."
            ),
            "openai_internal_error": (
                "O provider externo retornou um erro interno temporario. "
                "O run foi preservado para rastreabilidade e nenhuma acao local foi executada."
            ),
            "openai_model_unavailable": (
                "O modelo configurado nao esta disponivel para este provider. "
                "Revise a configuracao do modelo; nenhuma acao local foi executada."
            ),
            "openai_empty_response": (
                "O provider externo concluiu a chamada sem uma resposta utilizavel. "
                "Nenhuma acao local foi executada."
            ),
        }
        return messages.get(
            error_code,
            "O provider externo falhou de forma controlada. "
            "O run foi preservado para diagnostico e nenhuma acao local foi executada.",
        )

    def _fail(
        self,
        request: LucioAgentRequest,
        run_id: str,
        model: str,
        decision: LucioRouteDecision,
        error_code: str,
        text: str,
        memory_refs: list[str],
        memory_warnings: list[str],
        *,
        status: str,
    ) -> LucioAgentResponse:
        assistant = self.kernel.add_message(
            self.agent_id,
            request.session_id,
            AgentMessageCreateRequest(
                role="error",
                message_kind="error_message",
                content_sanitized=text,
                run_id=run_id,
                metadata_sanitized={"error_code": error_code},
            ),
        )
        self.kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status=status,
                final_message_id=assistant.message_id,
                error_code=error_code,
                memory_refs_used=memory_refs,
                memory_warnings=memory_warnings,
            ),
        )
        self._event(
            run_id,
            "lucio_request_failed" if status == "failed" else "lucio_request_blocked",
            text,
            {"error_code": error_code},
            severity="error" if status == "failed" else "warning",
            status=status,
        )
        return LucioAgentResponse(
            session_id=request.session_id,
            run_id=run_id,
            status=status,
            model=model,
            text=text,
            public_reasoning_summary=self._route_summary(decision),
            route_decision=decision,
            evidence_refs=[f"run:{run_id}"],
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
            error_code=error_code,
        )

    def _load_memory(self, run_id: str, request: LucioAgentRequest) -> tuple[str, list[str], list[str]]:
        if not self.config_service.runtime().use_memory_gateway:
            return "", [], []
        try:
            result = self.memory_gateway.load_context_for_run(
                MemoryContextLoadRequest(
                    agent_id=self.agent_id,
                    session_id=request.session_id,
                    run_id=run_id,
                    workspace_id=request.workspace_id,
                    limit=8,
                    max_chars=12000,
                    reason="lucio_strategic_context",
                )
            )
            return result.context_sanitized, result.memory_refs_used, result.warnings
        except Exception as exc:
            return "", [], [f"memory_context_load_failed:{type(exc).__name__}"]

    def _create_memory_candidate(self, response: LucioAgentResponse) -> None:
        if response.status not in {"completed", "delegation_running", "completed_with_warnings"}:
            return
        if response.multimodal_message and response.multimodal_message.image_artifact_ids:
            self._event(
                response.run_id,
                "lucio_multimodal_memory_write_skipped",
                "Memoria automatica ignorada para imagem/anexo visual; apenas evidence_refs sanitizadas foram preservadas.",
                {
                    "image_artifact_count": len(response.multimodal_message.image_artifact_ids),
                    "redaction_status": response.multimodal_message.redaction_status,
                },
            )
            return
        try:
            candidate = self.memory_gateway.create_candidate(
                MemoryCandidateCreateRequest(
                    proposed_by_agent_id=self.agent_id,
                    namespace="memory:lucio",
                    scope="private",
                    title=f"Lucio {response.route_decision.route}",
                    content_sanitized=response.text[:2000],
                    memory_type="workflow_lesson",
                    source_ref=f"run:{response.run_id}",
                    evidence_refs=response.evidence_refs,
                    confidence="medium",
                    reason_to_remember="lucio_agent_run_summary",
                    session_id=response.session_id,
                    run_id=response.run_id,
                    metadata_sanitized={
                        "route": response.route_decision.route,
                        "status": response.status,
                    },
                )
            )
            self._event(
                response.run_id,
                "lucio_memory_candidate_created",
                "Lucio criou um candidato de memoria privada para revisao.",
                {"candidate_id": candidate.candidate_id},
            )
        except Exception as exc:
            self._event(
                response.run_id,
                "lucio_memory_candidate_warning",
                "O candidato de memoria nao foi criado; a resposta principal foi preservada.",
                {"error_type": type(exc).__name__},
                severity="warning",
                status="warning",
            )

    def _provider_context(self, memory_context: str, request: LucioAgentRequest, multimodal_context: str = "") -> str:
        parts: list[str] = []
        if memory_context:
            parts.append(f"Memoria governada sanitizada:\n{memory_context}")
        if multimodal_context:
            parts.append(multimodal_context)
        if request.artifacts:
            rows = [
                {
                    "artifact_id": artifact.artifact_id,
                    "filename": artifact.filename,
                    "content_type": artifact.content_type,
                    "purpose": artifact.purpose,
                }
                for artifact in request.artifacts
            ]
            parts.append(f"Fontes de evidencia anexadas (metadados sanitizados):\n{redact_payload(rows)}")
        return "\n\n".join(parts)

    def _route_summary(self, decision: LucioRouteDecision) -> str:
        if decision.route in {"direct_response", "answer_directly"}:
            return "O pedido pode ser respondido estrategicamente sem ferramentas locais."
        if decision.route in {"delegate_codex"} or decision.route_type == "delegate_to_codex":
            return "O pedido exige trabalho tecnico; Codex foi selecionado como executor governado."
        if decision.route in {"delegate_aipinho"} or decision.route_type == "delegate_to_aipinho":
            return "O pedido exige contexto ou execucao local; AIpinho foi selecionada pelo fluxo governado."
        if decision.route in {"request_better_image", "ask_clarification"}:
            return decision.clarification_question or "Lucio precisa de esclarecimento antes de concluir."
        return "A politica nao encontrou uma rota segura para o pedido."

    def _risk_level(self, request: LucioAgentRequest) -> str:
        high_risk = {"shell", "workspace_write", "patch_apply", "git_write", "network_shell"}
        return "medium" if high_risk.intersection(request.requested_capabilities) else "low"

    def _event(
        self,
        run_id: str,
        event_type: str,
        message: str,
        payload: dict[str, Any],
        *,
        severity: str = "info",
        status: str = "received",
    ) -> None:
        try:
            self.kernel.add_event(
                run_id,
                AgentEventCreateRequest(
                    event_type=event_type,
                    status=status,
                    severity=severity,
                    human_message=message,
                    technical_summary_sanitized=event_type,
                    payload_sanitized=redact_payload(payload),
                    evidence_refs=[f"run:{run_id}"],
                ),
            )
        except FileNotFoundError:
            return
