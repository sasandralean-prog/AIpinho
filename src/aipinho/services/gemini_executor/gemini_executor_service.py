from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.memory import MemoryCandidateCreateRequest, MemoryContextLoadRequest
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.schemas.gemini_executor import (
    GeminiExecutorMessage,
    GeminiExecutorRequest,
    GeminiExecutorResponse,
    GeminiExecutorSession,
    GeminiStructuredAction,
)
from aipinho.core.paths import PATHS
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner
from aipinho.services.agents.agent_memory_gateway_service import AgentMemoryGatewayService
from aipinho.services.agents.agent_request_enrichment_service import AgentRequestEnrichmentService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.events.event_core import EventPublisherService, redact_payload
from aipinho.services.gemini_executor.gemini_executor_client import FakeGeminiClient, GeminiApiClient
from aipinho.services.gemini_executor.gemini_executor_config_service import GeminiExecutorConfigService
from aipinho.services.gemini_executor.gemini_executor_policy_service import GeminiExecutorPolicyService
from aipinho.services.gemini_executor.gemini_executor_session_store import GeminiExecutorSessionStore
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService


class GeminiExecutorService:
    def __init__(
        self,
        *,
        config_service: GeminiExecutorConfigService | None = None,
        session_store: GeminiExecutorSessionStore | None = None,
        client: Any | None = None,
        agent_kernel: AgentSessionKernelService | None = None,
        delegation_service: AgentDelegationService | None = None,
        memory_gateway: AgentMemoryGatewayService | None = None,
        local_action_planner: AgentLocalActionPlanner | None = None,
        request_enrichment: AgentRequestEnrichmentService | None = None,
    ) -> None:
        self.config_service = config_service or GeminiExecutorConfigService()
        self.store = session_store or GeminiExecutorSessionStore()
        self.policy = GeminiExecutorPolicyService()
        self._client = client
        self.agent_kernel = agent_kernel or AgentSessionKernelService()
        self.delegation_service = delegation_service or AgentDelegationService(kernel=self.agent_kernel)
        self.memory_gateway = memory_gateway or AgentMemoryGatewayService(kernel=self.agent_kernel)
        self.local_action_planner = local_action_planner or AgentLocalActionPlanner(AgentToolGatewayService(kernel=self.agent_kernel))
        self.request_enrichment = request_enrichment or AgentRequestEnrichmentService()
        self.capability_registry = self._capability_registry()

    def health(self) -> dict[str, object]:
        status = self.config_service.status()
        return {"status": "ok" if status.enabled else "disabled", "agent_id": "gemini_executor", "provider": "gemini", "config": status.model_dump()}

    def create_session(self, title: str = "Gemini Executor") -> GeminiExecutorSession:
        session = self.store.create(title)
        self._publish("gemini_executor_session_created", "Sessao Gemini Executor criada.", {"session_id": session.session_id})
        return session

    def sessions(self) -> list[GeminiExecutorSession]:
        return sorted(self.store.list(), key=lambda session: session.updated_at, reverse=True)

    def get_session(self, session_id: str) -> GeminiExecutorSession | None:
        return self.store.get(session_id)

    def rename_session(self, session_id: str, title: str) -> GeminiExecutorSession | None:
        session = self.store.rename(session_id, title)
        if session is not None:
            self._publish("gemini_executor_session_renamed", "Sessao Gemini Executor renomeada.", {"session_id": session_id})
        return session

    def delete_session(self, session_id: str) -> bool:
        deleted = self.store.delete(session_id)
        if deleted:
            self._publish("gemini_executor_session_deleted", "Sessao Gemini Executor removida.", {"session_id": session_id}, status="deleted")
        return deleted

    def messages(self, session_id: str) -> list[GeminiExecutorMessage]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        return self.store.messages(session_id)

    def events(self, run_id: str, *, after_event_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return [
            event.model_dump()
            for event in self.agent_kernel.list_run_events(run_id, include_hidden=False, after_event_id=after_event_id, limit=limit)
        ]

    def mobile_view_model(self, session_id: str, *, after_event_id: str | None = None) -> dict[str, object]:
        session = self.store.get(session_id)
        if session is None:
            raise FileNotFoundError(session_id)
        messages = self.store.messages(session_id)
        last_run_id = None
        for message in reversed(messages):
            last_run_id = message.metadata.get("run_id") if isinstance(message.metadata, dict) else None
            if last_run_id:
                break
        run = self.agent_kernel.get_run(str(last_run_id)) if last_run_id else None
        events = self.events(str(last_run_id), after_event_id=after_event_id) if last_run_id else []
        if run is not None:
            child_run_id = str(run.metadata_sanitized.get("child_run_id") or "")
            if child_run_id:
                child_events = [
                    {**event.model_dump(), "source_parent_run_id": run.run_id, "source_child_run_id": child_run_id}
                    for event in self.agent_kernel.list_run_events(child_run_id, include_hidden=False, limit=100)
                ]
                events.extend(child_events)
        return {
            "status": "ok",
            "agent_id": "gemini",
            "provider": "gemini",
            "cloud_warning_visible": self.config_service.runtime().cloud_warning_visible,
            "raw_default_visible": False,
            "token_in_url": False,
            "session": session.model_dump(),
            "active_run": run.model_dump() if run else None,
            "messages": [message.model_dump() for message in messages],
            "events": events,
        }

    def send(self, request: GeminiExecutorRequest) -> GeminiExecutorResponse:
        if self.store.get(request.session_id) is None:
            raise FileNotFoundError(request.session_id)
        request = self._enrich_request(request)
        config = self.config_service.runtime()
        model = request.model or config.default_model
        prompt = request.prompt[: config.max_prompt_chars]
        operation_workspace = request.workspace_context or (request.target_paths[0] if request.target_paths else None)
        kernel_session, kernel_run = self._create_kernel_run(request)
        memory_refs, memory_warnings = self._load_memory_context(kernel_run.run_id) if config.use_memory_gateway else ([], [])
        self._event(
            kernel_run.run_id,
            "gemini_run_started",
            "Run Gemini iniciado com governanca multiagente.",
            payload={"operation_type": request.operation_type, "model": model},
        )
        if memory_refs or memory_warnings:
            self._event(
                kernel_run.run_id,
                "gemini_memory_context_loaded",
                "Contexto de memoria Gemini carregado.",
                payload={"memory_refs": memory_refs, "warnings": memory_warnings},
                severity="warning" if memory_warnings else "info",
                status="loaded",
            )
        policy_decision = self.policy.evaluate(config=config, workspace_path=operation_workspace, requested_capabilities=request.requested_capabilities)
        self.store.add_message(GeminiExecutorMessage(session_id=request.session_id, role="user", content=request.prompt, metadata={"agent_id": "gemini_executor"}))
        if not policy_decision["allowed"]:
            self.agent_kernel.update_run(
                kernel_run.run_id,
                AgentRunUpdateRequest(status="blocked", error_code="gemini_executor_policy_blocked", metadata_sanitized={"policy": redact_payload(policy_decision)}),
            )
            response = GeminiExecutorResponse(
                session_id=request.session_id,
                run_id=kernel_run.run_id,
                status="blocked",
                model=model,
                text="O Gemini Executor foi bloqueado pela politica antes de executar qualquer acao.",
                structured_actions=[
                    GeminiStructuredAction(
                        action_type=request.operation_type,
                        status="blocked",
                        reason=",".join(policy_decision["reasons"]),
                        requires_approval=bool(policy_decision.get("requires_approval")),
                        policy_decision=policy_decision,
                    )
                ],
                error_code="gemini_executor_policy_blocked",
                human_error="A politica governada bloqueou esta solicitacao do Gemini Executor.",
                evidence_refs=[f"run:{kernel_run.run_id}"],
                memory_refs_used=memory_refs,
                warnings=memory_warnings,
            )
            self._store_response(response, policy_decision)
            self._publish("gemini_executor_blocked", response.text, {"operation_id": response.operation_id, "policy": policy_decision}, severity="warning", status="blocked")
            return response
        if self._requires_delegation(request) and config.use_delegation and config.prefer_aipinho_executor:
            response = self._delegate_to_aipinho(request, kernel_run.run_id, model, policy_decision, memory_refs, memory_warnings)
            self._store_response(response, policy_decision)
            self._create_memory_candidate(kernel_run.run_id, response)
            return response
        if self._requires_delegation(request) and not config.allow_direct_local_tools:
            self.agent_kernel.update_run(
                kernel_run.run_id,
                AgentRunUpdateRequest(
                    status="blocked",
                    error_code="gemini_local_execution_requires_delegation",
                    metadata_sanitized={"delegation_enabled": config.use_delegation},
                ),
            )
            response = GeminiExecutorResponse(
                session_id=request.session_id,
                run_id=kernel_run.run_id,
                status="blocked",
                model=model,
                text="A solicitacao exige execucao local, mas a delegacao governada nao esta disponivel.",
                error_code="gemini_local_execution_requires_delegation",
                human_error="Ative a delegacao governada para executar capacidades locais com seguranca.",
                evidence_refs=[f"run:{kernel_run.run_id}"],
                memory_refs_used=memory_refs,
                warnings=memory_warnings,
            )
            self._store_response(response, policy_decision)
            self._event(
                kernel_run.run_id,
                "gemini_run_blocked",
                response.text,
                payload={"reason_code": response.error_code},
                severity="warning",
                status="blocked",
            )
            return response
        client = self._client or self._client_from_config(config)
        self._event(kernel_run.run_id, "gemini_run_planning", "Gemini vai responder diretamente; execucao local nao foi necessaria.", payload={"mode": "direct_response"})
        self._publish("gemini_executor_request_created", "Pedido enviado ao Gemini Executor.", {"session_id": request.session_id, "operation_type": request.operation_type, "model": model})
        result = client.generate(prompt=prompt, model=model, timeout_seconds=config.timeout_seconds, max_output_chars=request.max_output_chars or config.max_output_chars)
        if result.fallback_used:
            self._publish("gemini_executor_key_fallback_used", "Fallback sanitizado para chave alternativa do Gemini Executor.", {"provider": "gemini", "model": model})
        if result.status != "completed":
            self.agent_kernel.update_run(
                kernel_run.run_id,
                AgentRunUpdateRequest(status="failed", error_code=result.error_code or "gemini_provider_error"),
            )
            response = GeminiExecutorResponse(
                session_id=request.session_id,
                run_id=kernel_run.run_id,
                status="failed",
                model=model,
                text="O provedor Gemini falhou de forma controlada. Nenhuma acao com efeito colateral foi executada.",
                error_code=result.error_code or "gemini_provider_error",
                human_error="Falha controlada no provedor externo Gemini.",
                evidence_refs=[f"run:{kernel_run.run_id}"],
                memory_refs_used=memory_refs,
                warnings=memory_warnings,
            )
            self._store_response(response, policy_decision)
            self._publish("gemini_executor_failed", response.text, {"operation_id": response.operation_id, "error_code": response.error_code}, severity="error", status="failed")
            return response
        self.agent_kernel.update_run(kernel_run.run_id, AgentRunUpdateRequest(status="completed", metadata_sanitized={"direct_response": True}))
        self._event(kernel_run.run_id, "gemini_explanation", "Gemini respondeu diretamente com provider cloud/fake configurado.", payload={"model": result.model, "fallback_used": result.fallback_used}, status="completed")
        response = GeminiExecutorResponse(
            session_id=request.session_id,
            run_id=kernel_run.run_id,
            status="completed",
            model=result.model,
            text=result.text,
            fallback_used=result.fallback_used,
            structured_actions=self._actions_for_request(request, policy_decision),
            evidence_refs=[f"run:{kernel_run.run_id}"],
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
        )
        self._store_response(response, policy_decision)
        self._create_memory_candidate(kernel_run.run_id, response)
        self._publish("gemini_executor_response_received", "Resposta recebida do Gemini Executor.", {"operation_id": response.operation_id, "model": response.model, "fallback_used": response.fallback_used}, status="completed")
        self._publish("gemini_executor_completed", "Gemini Executor concluiu a resposta sem aplicar efeitos colaterais.", {"operation_id": response.operation_id}, status="completed")
        return response

    def _enrich_request(self, request: GeminiExecutorRequest) -> GeminiExecutorRequest:
        enrichment = self.request_enrichment.enrich(
            prompt=request.prompt,
            operation_type=request.operation_type,
            requested_capabilities=request.requested_capabilities,
            workspace_context=request.workspace_context,
            target_paths=request.target_paths,
        )
        return request.model_copy(
            update={
                "operation_type": enrichment.operation_type or request.operation_type,
                "requested_capabilities": enrichment.requested_capabilities,
                "workspace_context": enrichment.workspace_context,
                "target_paths": enrichment.target_paths,
            }
        )

    def _try_local_create_file(
        self,
        request: GeminiExecutorRequest,
        run_id: str,
        model: str,
        policy_decision: dict[str, Any],
        memory_refs: list[str],
        memory_warnings: list[str],
    ) -> GeminiExecutorResponse | None:
        workspace_context = request.workspace_context or (request.target_paths[0] if request.target_paths else None)
        result = self.local_action_planner.run_explicit_create_file(
            agent_id="gemini",
            run_id=run_id,
            prompt=request.prompt,
            workspace_context=workspace_context,
            requested_capabilities=request.requested_capabilities,
            execution_mode=self.config_service.runtime().default_execution_mode,
            metadata_sanitized={"source": "gemini_executor_local_action_planner"},
        )
        if result is None:
            return None
        status = "completed" if result.status == "succeeded" else ("blocked" if result.status in {"blocked", "approval_required"} else "failed")
        self.agent_kernel.update_run(
            run_id,
            AgentRunUpdateRequest(
                status=status,
                error_code=result.tool_invocation.error_code,
                metadata_sanitized={
                    "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                    "tool_name": result.tool_invocation.tool_name,
                    "tool_status": result.status,
                },
            ),
        )
        self._event(
            run_id,
            "gemini_local_tool_completed" if result.status == "succeeded" else "gemini_local_tool_not_completed",
            "Gemini Executor acionou uma ferramenta local governada via Tool Gateway.",
            payload={
                "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                "tool_name": result.tool_invocation.tool_name,
                "status": result.status,
                "block_reason_code": result.tool_invocation.block_reason_code,
            },
            severity="info" if result.status == "succeeded" else "warning",
            status=result.status,
        )
        text = (
            "Executei a ação local pelo Tool Gateway governado.\n"
            f"Ferramenta: {result.tool_invocation.tool_name}\n"
            f"Status: {result.status}\n"
            f"Evidência: {result.tool_invocation.output_summary_sanitized or result.tool_invocation.tool_invocation_id}"
        )
        return GeminiExecutorResponse(
            session_id=request.session_id,
            run_id=run_id,
            status=status,
            model=model,
            text=text,
            structured_actions=self._actions_for_request(request, policy_decision),
            evidence_refs=[f"run:{run_id}", f"tool:{result.tool_invocation.tool_invocation_id}"],
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
        )

    def _create_kernel_run(self, request: GeminiExecutorRequest):
        session = self.agent_kernel.create_session(
            "gemini",
            AgentSessionCreateRequest(
                title=f"Gemini bridge {request.session_id[-8:]}",
                active_workspace_id=request.workspace_id,
                metadata_sanitized={
                    "gemini_executor_session_id": request.session_id,
                    "bridge": "gemini_executor_multi_agent",
                    "provider": "gemini",
                },
            ),
        )
        run = self.agent_kernel.create_run(
            "gemini",
            session.session_id,
            AgentRunCreateRequest(
                operation_type=request.operation_type,
                status="running",
                workspace_id=request.workspace_id,
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={
                    "gemini_executor_session_id": request.session_id,
                    "execution_mode": self.config_service.runtime().default_execution_mode,
                    "workspace_context_present": bool(request.workspace_context),
                    "target_path_count": len(request.target_paths),
                },
            ),
        )
        return session, run

    def _load_memory_context(self, run_id: str) -> tuple[list[str], list[str]]:
        try:
            context = self.memory_gateway.load_context_for_run(
                MemoryContextLoadRequest(
                    agent_id="gemini",
                    run_id=run_id,
                    limit=10,
                    max_chars=16000,
                    reason="gemini_run_start",
                )
            )
            return context.memory_refs_used, context.warnings
        except Exception as exc:
            return [], [f"memory_context_load_failed:{type(exc).__name__}"]

    def _requires_delegation(self, request: GeminiExecutorRequest) -> bool:
        local_capabilities = {
            "read_workspace",
            "scan_workspace",
            "search_workspace",
            "workspace_write",
            "create_file",
            "modify_file",
            "create_directory",
            "artifact_create",
            "report_generate",
            "validation",
            "shell",
            "run_approved_shell",
            "build",
            "test",
        }
        local_operations = {
            "local_execution",
            "readonly_analysis",
            "artifact_request",
            "validation",
            "report_generate",
            "workspace_operation",
            "delegated_governed_execution",
            "operational_task_request",
            "coding",
            "build",
            "test",
        }
        return bool(
            request.workspace_context
            or request.workspace_id
            or request.target_paths
            or (set(request.requested_capabilities) & local_capabilities)
            or request.operation_type in local_operations
        )

    def _delegation_capabilities(self, request: GeminiExecutorRequest) -> list[str]:
        if request.requested_capabilities:
            return self._canonical_capabilities(request.requested_capabilities)
        if request.workspace_context or request.workspace_id or request.target_paths:
            return ["read_workspace"]
        return []

    def _delegation_operation(self, request: GeminiExecutorRequest) -> str:
        capabilities = set(self._canonical_capabilities(request.requested_capabilities))
        read_caps = {"read_workspace"}
        write_caps = {"write_workspace", "shell", "patch_preview", "patch_apply"}
        validation_caps = {"validation"}
        build_test_caps = {"build", "test"}
        if capabilities & build_test_caps or (capabilities & read_caps and capabilities & write_caps and capabilities & validation_caps):
            return "delegated_governed_execution"
        if request.operation_type.startswith("gemini_"):
            if capabilities & {"write_workspace"}:
                return "workspace_operation"
            if capabilities & {"artifact_write"}:
                return "artifact_request"
            if request.workspace_context or request.workspace_id or request.target_paths:
                return "readonly_analysis"
        return request.operation_type

    def _capability_registry(self) -> CapabilityRegistryService | None:
        path = PATHS.config_root / "policies" / "capability_registry.yaml"
        if not path.exists():
            return None
        try:
            return CapabilityRegistryService(path).load()
        except Exception:
            return None

    def _canonical_capabilities(self, capabilities: list[str]) -> list[str]:
        if self.capability_registry is None:
            return capabilities
        return self.capability_registry.canonicalize_all(capabilities)

    def _delegate_to_aipinho(
        self,
        request: GeminiExecutorRequest,
        parent_run_id: str,
        model: str,
        policy_decision: dict[str, Any],
        memory_refs: list[str],
        memory_warnings: list[str],
    ) -> GeminiExecutorResponse:
        self._event(parent_run_id, "gemini_delegation_intent_detected", "Pedido exige capacidade local; Gemini vai delegar para AIpinho.", payload={"target_agent_id": "aipinho"})
        try:
            delegation = self.delegation_service.create_delegation(
                "gemini",
                parent_run_id,
                DelegationCreateRequest(
                    target_agent_id="aipinho",
                    user_goal=request.prompt,
                    requested_operation=self._delegation_operation(request),
                    operation_type=self._delegation_operation(request),
                    workspace_id=request.workspace_id,
                    capabilities_requested=self._delegation_capabilities(request),
                    constraints={"workspace_context": bool(request.workspace_context), "target_path_count": len(request.target_paths)},
                    expected_outputs=["execution_trace", "human_summary"],
                    memory_refs=memory_refs,
                    risk_level="medium" if any(cap in request.requested_capabilities for cap in {"workspace_write", "shell", "run_approved_shell"}) else "low",
                    execution_mode=self.config_service.runtime().default_execution_mode,
                    metadata_sanitized={"provider": "gemini", "gemini_session_id": request.session_id},
                ),
            )
        except Exception as exc:
            self.agent_kernel.update_run(parent_run_id, AgentRunUpdateRequest(status="failed", error_code=type(exc).__name__))
            return GeminiExecutorResponse(
                session_id=request.session_id,
                run_id=parent_run_id,
                status="failed",
                model=model,
                text="Gemini tentou delegar para a AIpinho, mas a criacao da delegacao falhou de forma controlada.",
                error_code=type(exc).__name__,
                human_error="Falha controlada ao criar DelegationRequest.",
                evidence_refs=[f"run:{parent_run_id}"],
                memory_refs_used=memory_refs,
                warnings=[*memory_warnings, f"delegation_failed:{type(exc).__name__}"],
            )
        status = "delegation_running" if delegation.status == "running" else delegation.status
        if delegation.status in {"blocked", "failed", "approval_required"}:
            run_status = {
                "blocked": "blocked",
                "failed": "failed",
                "approval_required": "pending_approval",
            }[delegation.status]
            self.agent_kernel.update_run(parent_run_id, AgentRunUpdateRequest(status=run_status, metadata_sanitized={"delegation_id": delegation.delegation.delegation_id}))
        else:
            self.agent_kernel.update_run(parent_run_id, AgentRunUpdateRequest(status="delegation_running", metadata_sanitized={"delegation_id": delegation.delegation.delegation_id, "child_run_id": delegation.delegation.child_run_id}))
        child_events = []
        if delegation.delegation.child_run_id:
            child_events = self.agent_kernel.list_run_events(delegation.delegation.child_run_id, include_hidden=False, limit=20)
        evidence_refs = [
            f"run:{parent_run_id}",
            f"delegation:{delegation.delegation.delegation_id}",
            *([f"run:{delegation.delegation.child_run_id}"] if delegation.delegation.child_run_id else []),
        ]
        result_summary = delegation.result.summary if delegation.result else "Delegacao criada sem resultado final ainda."
        if delegation.delegation.child_run_id:
            text = (
                "Deleguei a execucao local para a AIpinho.\n"
                f"Status da delegacao: {delegation.status}.\n"
                f"Resumo: {result_summary}\n"
                "Vou usar os eventos do child run como fonte de verdade antes de declarar qualquer conclusao."
            )
        else:
            reason = delegation.result.reason_code if delegation.result else delegation.status
            text = (
                "A delegacao Gemini -> AIpinho nao iniciou execucao real.\n"
                f"Status da delegacao: {delegation.status}.\n"
                f"Motivo: {reason}.\n"
                f"Resumo: {result_summary}\n"
                "Nenhum child run foi criado, nenhum arquivo foi alterado e nenhum artifact foi declarado como produzido."
            )
        self._event(
            parent_run_id,
            "gemini_delegation_created",
            "DelegationRequest Gemini -> AIpinho criada.",
            payload={
                "delegation_id": delegation.delegation.delegation_id,
                "child_run_id": delegation.delegation.child_run_id,
                "status": delegation.status,
                "child_event_count": len(child_events),
            },
            status=delegation.status,
        )
        return GeminiExecutorResponse(
            session_id=request.session_id,
            run_id=parent_run_id,
            status=status,
            model=model,
            text=text,
            structured_actions=self._actions_for_request(request, policy_decision),
            delegation_id=delegation.delegation.delegation_id,
            child_run_id=delegation.delegation.child_run_id,
            evidence_refs=evidence_refs,
            memory_refs_used=memory_refs,
            warnings=memory_warnings,
        )

    def _create_memory_candidate(self, run_id: str, response: GeminiExecutorResponse) -> None:
        if response.status not in {"completed", "delegation_running", "completed_with_warnings"}:
            return
        try:
            candidate = self.memory_gateway.create_candidate(
                MemoryCandidateCreateRequest(
                    proposed_by_agent_id="gemini",
                    namespace="memory:gemini",
                    scope="private",
                    title=f"Gemini run {response.status}",
                    content_sanitized=response.text[:2000],
                    memory_type="workflow_lesson",
                    source_ref=f"run:{run_id}",
                    evidence_refs=response.evidence_refs or [f"run:{run_id}"],
                    confidence="medium",
                    reason_to_remember="gemini_agent_run_summary",
                    session_id=response.session_id,
                    run_id=run_id,
                    metadata_sanitized={"status": response.status, "delegation_id": response.delegation_id},
                )
            )
            self._event(run_id, "gemini_memory_candidate_created", "Memory candidate Gemini criado.", payload={"candidate_id": candidate.candidate_id}, status="created")
        except Exception as exc:
            self._event(run_id, "gemini_memory_warning", "Memory candidate Gemini nao foi criado.", payload={"error_type": type(exc).__name__}, severity="warning", status="warning")

    def _event(self, run_id: str, event_type: str, message: str, *, payload: dict[str, Any] | None = None, severity: str = "info", status: str = "info") -> None:
        try:
            self.agent_kernel.add_event(
                run_id,
                AgentEventCreateRequest(
                    event_type=event_type,
                    severity=severity,
                    status=status,
                    human_message=message,
                    technical_summary_sanitized=event_type,
                    payload_sanitized=redact_payload(payload or {}),
                    evidence_refs=[f"run:{run_id}"],
                ),
            )
        except FileNotFoundError:
            return

    def preview(self, request: GeminiExecutorRequest) -> GeminiExecutorResponse:
        request = request.model_copy(update={"operation_type": "gemini_patch_preview", "requested_capabilities": list(set(request.requested_capabilities + ["create_patch_preview"]))})
        response = self.send(request)
        if response.status == "completed":
            response = response.model_copy(update={"status": "preview_created", "text": response.text + "\n\nPreview governado criado como proposta. Apply exige approval e validacao."})
            self._publish("gemini_executor_patch_preview_created", "Preview de patch Gemini criado sem apply.", {"operation_id": response.operation_id}, status="preview_created")
        return response

    def request_approval(self, session_id: str, operation_id: str | None = None) -> dict[str, object]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        approval_id = f"gemini_approval_pending_{operation_id or session_id}"
        payload = {"status": "pending_approval", "approval_id": approval_id, "session_id": session_id, "agent_id": "gemini_executor", "operation_id": operation_id}
        self._publish("gemini_executor_approval_requested", "Approval Gemini solicitado para acao governada.", payload, severity="warning", status="pending_approval")
        return payload

    def guarded_not_implemented(self, session_id: str, action: str) -> dict[str, object]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        payload = {"status": "blocked", "agent_id": "gemini_executor", "action": action, "reason": "governed_pipeline_required"}
        self._publish("gemini_executor_blocked", "Acao Gemini bloqueada ate existir approval/pipeline governado valido.", payload, severity="warning", status="blocked")
        return payload

    def _client_from_config(self, config) -> GeminiApiClient:
        return GeminiApiClient(config.primary_key, config.secondary_key, api_keys=config.api_keys)

    def _actions_for_request(self, request: GeminiExecutorRequest, policy_decision: dict[str, Any]) -> list[GeminiStructuredAction]:
        actions: list[GeminiStructuredAction] = []
        for capability in request.requested_capabilities:
            if capability in {"create_patch_preview", "apply_approved_patch", "run_approved_shell"}:
                actions.append(
                    GeminiStructuredAction(
                        action_type=capability,
                        status="pending_approval" if policy_decision.get("requires_approval") else "preview_only",
                        reason="side_effect_requires_governed_pipeline",
                        capability=capability,
                        requires_approval=bool(policy_decision.get("requires_approval")),
                        validation_required=True,
                        policy_decision=policy_decision,
                    )
                )
        return actions

    def _store_response(self, response: GeminiExecutorResponse, policy_decision: dict[str, Any]) -> None:
        self.store.add_message(
            GeminiExecutorMessage(
                session_id=response.session_id,
                role="assistant",
                content=response.text,
                operation_id=response.operation_id,
                metadata={
                    "agent_id": "gemini_executor",
                    "status": response.status,
                    "run_id": response.run_id,
                    "delegation_id": response.delegation_id,
                    "child_run_id": response.child_run_id,
                    "evidence_refs": response.evidence_refs,
                    "memory_refs_used": response.memory_refs_used,
                    "policy_decision": redact_payload(policy_decision),
                },
            )
        )

    def _publish(self, event_type: str, summary: str, payload: dict[str, Any], *, severity: str = "info", status: str = "created") -> None:
        try:
            EventPublisherService().publish(
                EventPublishRequest(
                    event_type=event_type,
                    source_service="gemini_executor",
                    human_summary=summary,
                    payload=redact_payload(payload),
                    severity=severity,
                    status=status,
                    visibility="public",
                    copy_policy="copy_sanitized",
                )
            )
        except ValueError:
            return
