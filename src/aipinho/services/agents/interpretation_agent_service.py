from __future__ import annotations

from typing import Any

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentMessageCreateRequest, AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.hybrid_execution import CanonicalPromptRequest, IslandChatRequest, IslandChatResponse
from aipinho.schemas.gemini_executor import GeminiExecutorRequest
from aipinho.schemas.lucio_agent import LucioAgentRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_text_artifact_service import AgentTextArtifactService
from aipinho.services.agents.canonical_prompt_builder_service import CanonicalPromptBuilderService
from aipinho.services.agents.hybrid_execution_policy_service import HybridExecutionPolicyService
from aipinho.services.gemini_executor import GeminiExecutorService
from aipinho.services.lucio_agent import LucioAgentService


class InterpretationAgentService:
    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        delegations: AgentDelegationService | None = None,
        artifacts: AgentTextArtifactService | None = None,
        prompt_builder: CanonicalPromptBuilderService | None = None,
        policy: HybridExecutionPolicyService | None = None,
        lucio: LucioAgentService | None = None,
        gemini: GeminiExecutorService | None = None,
    ) -> None:
        self.kernel = kernel or AgentSessionKernelService()
        self.delegations = delegations or AgentDelegationService(kernel=self.kernel)
        self.artifacts = artifacts or AgentTextArtifactService()
        self.prompt_builder = prompt_builder or CanonicalPromptBuilderService()
        self.policy = policy or HybridExecutionPolicyService()
        self.lucio = lucio or LucioAgentService(kernel=self.kernel, delegation_service=self.delegations)
        self.gemini = gemini or GeminiExecutorService(agent_kernel=self.kernel, delegation_service=self.delegations)

    def chat(self, source_agent: str, request: IslandChatRequest) -> IslandChatResponse:
        if source_agent not in set(self.policy.islands().get("allowed_agents", [])):
            raise ValueError("interpretation_agent_not_allowed")
        mode = self._mode(request)
        if mode == "artifact_text":
            return self._artifact(source_agent, request)
        if mode == "delegate_to_aipinho":
            return self._delegate(source_agent, request)
        return self._direct_chat(source_agent, request)

    def _mode(self, request: IslandChatRequest) -> str:
        if request.mode != "auto":
            return request.mode
        operational = set(self.policy.islands().get("operational_capabilities", []))
        if set(request.requested_capabilities) & operational or request.operation_type not in {"chat", "conversation", "text_analysis"}:
            return "delegate_to_aipinho"
        return "chat"

    def _delegate(self, source_agent: str, request: IslandChatRequest) -> IslandChatResponse:
        session = self._kernel_session(source_agent, request.session_id, request.workspace)
        run = self.kernel.create_run(
            source_agent,
            session.session_id,
            AgentRunCreateRequest(
                operation_type=f"{source_agent}_delegation",
                status="running",
                workspace_id=request.workspace,
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={"local_execution_allowed": False, "source_mode": "interpretation_delegation"},
            ),
        )
        self.kernel.add_message(source_agent, session.session_id, AgentMessageCreateRequest(role="user", content_sanitized=request.message, run_id=run.run_id))
        canonical = self.prompt_builder.build(
            CanonicalPromptRequest(
                user_message=request.message,
                source_agent=source_agent,
                workspace=request.workspace,
                intent=request.intent,
                constraints=request.constraints,
                desired_outputs=request.desired_outputs,
                validation_required=True,
            )
        )
        delegation = self.delegations.create_delegation(
            source_agent,
            run.run_id,
            DelegationCreateRequest(
                target_agent_id="aipinho",
                user_goal=canonical.canonical_prompt,
                requested_operation=request.operation_type if request.operation_type != "chat" else "local_execution",
                workspace_id=request.workspace,
                capabilities_requested=request.requested_capabilities,
                constraints={**request.constraints, "canonical_prompt": True, "local_tools_must_use_gateway": True},
                expected_outputs=request.desired_outputs or ["human_summary", "event_trace", "validation_evidence"],
                risk_level="low",
                execution_mode="governed_autorun",
                metadata_sanitized={"source_agent": source_agent, "interpretation_layer": True},
            ),
        )
        text = "Vou delegar esta execucao para a AIpinho. A AIpinho sera responsavel pela execucao local; vou resumir o resultado confirmado."
        message = self.kernel.add_message(
            source_agent,
            session.session_id,
            AgentMessageCreateRequest(
                role="assistant",
                message_kind="delegation_notice",
                content_sanitized=text,
                run_id=run.run_id,
                metadata_sanitized={"delegation_id": delegation.delegation.delegation_id, "executor_agent": "aipinho"},
            ),
        )
        self.kernel.update_run(run.run_id, AgentRunUpdateRequest(status="delegation_running", final_message_id=message.message_id, metadata_sanitized={"delegation_id": delegation.delegation.delegation_id, "child_run_id": delegation.delegation.child_run_id}))
        return IslandChatResponse(
            message_id=message.message_id,
            response_text=text,
            delegated=True,
            bridge_task_id=delegation.delegation.delegation_id,
            events_poll_url=f"/api/v1/agent-bridge/tasks/{delegation.delegation.delegation_id}/details",
            reason_code=delegation.result.reason_code if delegation.result else None,
            source_agent=source_agent,
            executor_agent="aipinho",
        )

    def _artifact(self, source_agent: str, request: IslandChatRequest) -> IslandChatResponse:
        session = self._kernel_session(source_agent, request.session_id, request.workspace)
        artifact = self.artifacts.create(
            source_agent=source_agent,
            content=request.message,
            session_id=session.session_id,
            filename=request.artifact_filename,
            artifact_kind=request.intent or "analysis",
        )
        text = "Gerei um artifact textual nesta ilha. Nao houve execucao local da AIpinho."
        message = self.kernel.add_message(
            source_agent,
            session.session_id,
            AgentMessageCreateRequest(role="assistant", message_kind="artifact_notice", content_sanitized=text, artifact_ids=[artifact["artifact_id"]]),
        )
        return IslandChatResponse(message_id=message.message_id, response_text=text, artifact_refs=[artifact], source_agent=source_agent, executor_agent=source_agent)

    def _direct_chat(self, source_agent: str, request: IslandChatRequest) -> IslandChatResponse:
        if source_agent == "lucio":
            session = self.lucio.get_session(request.session_id or "") or self.lucio.create_session("Lucio")
            response = self.lucio.send(LucioAgentRequest(session_id=session.session_id, prompt=request.message, operation_type="lucio_chat"))
            return IslandChatResponse(message_id=response.request_id, response_text=response.text, delegated=bool(response.delegation_id), bridge_task_id=response.delegation_id, source_agent="lucio", executor_agent="aipinho" if response.delegation_id else "lucio", reason_code=response.error_code)
        session = self.gemini.get_session(request.session_id or "") or self.gemini.create_session("Gemini")
        response = self.gemini.send(GeminiExecutorRequest(session_id=session.session_id, prompt=request.message, operation_type="gemini_chat"))
        return IslandChatResponse(message_id=response.request_id, response_text=response.text, delegated=bool(response.delegation_id), bridge_task_id=response.delegation_id, source_agent="gemini", executor_agent="aipinho" if response.delegation_id else "gemini", reason_code=response.error_code)

    def _kernel_session(self, source_agent: str, session_id: str | None, workspace: str | None):
        if session_id:
            existing = self.kernel.get_session(source_agent, session_id, include_compat=False)
            if existing is not None:
                return existing
        return self.kernel.create_session(source_agent, AgentSessionCreateRequest(title=f"{source_agent.title()} interpretation", active_workspace_id=workspace, metadata_sanitized={"local_execution_allowed": False}))

