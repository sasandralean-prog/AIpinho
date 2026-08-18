from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactUploadRequest
from aipinho.schemas.codex_agent import (
    CodexAgentRequest,
    CodexAgentResponse,
    CodexArtifact,
    CodexAutoApprovalDecision,
    CodexChatMessage,
    CodexChatSession,
    CodexRun,
    CodexRunEvent,
    CodexToolRequest,
)
from aipinho.schemas.agents.contracts import (
    AgentRunCreateRequest,
    AgentSessionCreateRequest,
)
from aipinho.schemas.agents.memory import (
    MemoryCandidateCreateRequest,
    MemoryContextLoadRequest,
)
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest, ToolInvocationResult
from aipinho.schemas.agents.ownership import WriteConflictCheckRequest
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.artifacts.artifact_interaction_core import ArtifactDownloadService, ArtifactUploadService
from aipinho.services.agents.agent_memory_gateway_service import AgentMemoryGatewayService
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.hybrid_execution_policy_service import HybridExecutionPolicyService
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService
from aipinho.services.codex_agent.codex_agent_config_service import CodexAgentConfigService
from aipinho.services.codex_agent.codex_agent_policy_service import CodexAgentPolicyService
from aipinho.services.codex_agent.codex_agent_store import CodexAgentStore
from aipinho.services.codex_agent.codex_cli_adapter import CodexCliAdapter, FakeCodexCliAdapter
from aipinho.services.events.event_core import EventPublisherService, redact_payload
from aipinho.schemas.events.contracts import utc_now_iso


class CodexAgentService:
    def __init__(
        self,
        *,
        config_service: CodexAgentConfigService | None = None,
        store: CodexAgentStore | None = None,
        adapter: Any | None = None,
        agent_kernel: AgentSessionKernelService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
        memory_gateway: AgentMemoryGatewayService | None = None,
        workspace_locks: WorkspaceLockService | None = None,
        hybrid_policy: HybridExecutionPolicyService | None = None,
    ) -> None:
        self.config_service = config_service or CodexAgentConfigService()
        self.store = store or CodexAgentStore()
        self.policy = CodexAgentPolicyService()
        self.adapter = adapter
        self.agent_kernel = agent_kernel or AgentSessionKernelService()
        self.tool_gateway = tool_gateway or AgentToolGatewayService(kernel=self.agent_kernel)
        self.local_action_planner = AgentLocalActionPlanner(self.tool_gateway)
        self.memory_gateway = memory_gateway or AgentMemoryGatewayService(kernel=self.agent_kernel)
        self.workspace_locks = workspace_locks or WorkspaceLockService()
        self.hybrid_policy = hybrid_policy or HybridExecutionPolicyService()

    def health(self) -> dict[str, object]:
        status = self.config_service.status()
        return {"status": "ok" if status.enabled and status.cli_detected else status.cli_status, "agent_id": "codex_agent", "config": status.model_dump()}

    def create_session(self, title: str = "Codex Agent") -> CodexChatSession:
        session = self.store.create(title)
        self._publish("codex_agent_session_created", "Sessao Codex Agent criada.", {"session_id": session.session_id})
        return session

    def sessions(self) -> list[CodexChatSession]:
        return sorted(self.store.list(), key=lambda session: session.updated_at, reverse=True)

    def get_session(self, session_id: str) -> CodexChatSession | None:
        return self.store.get(session_id)

    def rename_session(self, session_id: str, title: str) -> CodexChatSession | None:
        session = self.store.rename(session_id, title)
        if session:
            self._publish("codex_agent_session_renamed", "Sessao Codex Agent renomeada.", {"session_id": session_id})
        return session

    def delete_session(self, session_id: str) -> bool:
        deleted = self.store.delete(session_id)
        if deleted:
            self._publish("codex_agent_session_deleted", "Sessao Codex Agent removida.", {"session_id": session_id}, status="deleted")
        return deleted

    def messages(self, session_id: str) -> list[CodexChatMessage]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        return self.store.messages(session_id)

    def messages_after(self, session_id: str, *, after_message_id: str | None = None) -> list[CodexChatMessage]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        return self.store.messages(session_id, after_message_id=after_message_id)

    def runs(self, session_id: str | None = None) -> list[CodexRun]:
        return self.store.list_runs(session_id=session_id)

    def get_run(self, run_id: str) -> CodexRun | None:
        return self.store.get_run(run_id)

    def events(self, run_id: str, *, after_event_id: str | None = None, limit: int | None = None) -> list[CodexRunEvent]:
        config = self.config_service.runtime()
        return self.store.events(run_id, after_event_id=after_event_id, limit=limit or config.max_events_per_poll)

    def send(self, request: CodexAgentRequest) -> CodexAgentResponse:
        if self.store.get(request.session_id) is None:
            raise FileNotFoundError(request.session_id)
        config = self.config_service.runtime()
        status = self.config_service.status()
        autorun_enabled = config.autorun_enabled if request.autorun_enabled is None else request.autorun_enabled
        autoreview_enabled = config.autoreview_enabled if request.autoreview_enabled is None else request.autoreview_enabled
        autoapproval_enabled = config.autoapproval_enabled if request.autoapproval_enabled is None else request.autoapproval_enabled
        run = self.store.create_run(
            session_id=request.session_id,
            user_prompt=request.prompt,
            workspace_path=request.workspace_context,
            requested_capabilities=request.requested_capabilities,
            autorun_enabled=autorun_enabled,
            autoreview_enabled=autoreview_enabled,
            autoapproval_enabled=autoapproval_enabled,
            autopilot_mode=config.autopilot_mode if autorun_enabled else "off",
        )
        kernel_session, kernel_run = self._create_kernel_run(run, request)
        run = self.store.update_run(
            run.run_id,
            metadata={
                **run.metadata,
                "agent_kernel_session_id": kernel_session.session_id,
                "agent_kernel_run_id": kernel_run.run_id,
            },
        ) or run
        event_ids: list[str] = []
        event_ids.append(self._event(run, "codex_run_created", "Run criado", "Recebi sua tarefa e criei uma execucao Codex separada.").event_id)
        event_ids.append(self._event(run, "codex_run_started", "Run iniciado", "Vou avaliar policy, workspace e capacidades antes de executar.").event_id)
        if autorun_enabled:
            event_ids.append(self._event(run, "codex_run_autorun_enabled", "Autorun governado ativo", "Autorun esta ativo, limitado por policy e emergency stop.").event_id)
        memory_refs, memory_warnings = self._load_memory_context(run, kernel_run)
        if memory_refs or memory_warnings:
            run = self.store.update_run(
                run.run_id,
                metadata={
                    **run.metadata,
                    "memory_refs_used": memory_refs,
                    "memory_warnings": memory_warnings,
                },
            ) or run
            event_ids.append(
                self._event(
                    run,
                    "codex_memory_context_loaded",
                    "Memoria Codex carregada",
                    "Contexto governado de memoria foi carregado para a execucao Codex.",
                    payload={"memory_refs": memory_refs, "warnings": memory_warnings},
                    severity="warning" if memory_warnings else "info",
                    status="loaded",
                ).event_id
            )
        policy = self.policy.evaluate(config=config, workspace_path=request.workspace_context, requested_capabilities=request.requested_capabilities)
        lock_decision = self._direct_write_lock_decision(request, run.run_id)
        if lock_decision is not None and not lock_decision.allowed:
            policy = {
                **policy,
                "allowed": False,
                "reasons": sorted(set([*policy.get("reasons", []), lock_decision.reason_code or "workspace_locked_by_other_agent"])),
                "workspace_lock": lock_decision.model_dump(),
            }
        event_ids.append(self._event(run, "codex_run_policy_check", "Policy avaliada", self._policy_message(policy), payload=policy, severity="warning" if not policy["allowed"] else "info", status="blocked" if not policy["allowed"] else "allowed").event_id)
        for decision in self._autoapproval_decisions(run, request, policy):
            event_ids.append(
                self._event(
                    run,
                    "codex_auto_approval_granted" if decision.approved else "codex_auto_approval_denied",
                    "Auto approval aplicado" if decision.approved else "Auto approval bloqueado",
                    decision.reason,
                    payload=decision.model_dump(),
                    severity="info" if decision.approved else "warning",
                    status="approved" if decision.approved else "blocked",
                ).event_id
            )
        self.store.add_message(CodexChatMessage(session_id=request.session_id, role="user", content=request.prompt, run_id=run.run_id, message_kind="user_message", metadata={"agent_id": "codex_agent"}))
        if not policy["allowed"]:
            lock_blocked = bool(lock_decision is not None and not lock_decision.allowed)
            response = CodexAgentResponse(session_id=request.session_id, run_id=run.run_id, status="blocked", text="Codex Agent bloqueado pela politica antes de executar.", cli_status=status.cli_status, error_code="codex_workspace_locked_by_other_agent" if lock_blocked else "codex_agent_policy_blocked", human_error="O workspace possui ownership ativo de outro agente." if lock_blocked else "Policy/capability bloqueou esta solicitacao.", event_ids=event_ids, validation_status="not_started")
            event_ids.append(self._event(run, "codex_run_blocked", "Run bloqueado", response.human_error or response.text, payload={"policy": policy}, severity="warning", status="blocked").event_id)
            run = self.store.update_run(run.run_id, status="blocked", completed_at=utc_now_iso(), validation_status="not_started", error_code=response.error_code) or run
            self._store_response(response, policy, run_id=run.run_id)
            response = response.model_copy(update={"event_ids": event_ids, "final_message_id": self.store.messages(request.session_id)[-1].message_id})
            self._publish("codex_agent_blocked", response.text, {"operation_id": response.operation_id, "policy": policy}, severity="warning", status="blocked")
            return response
        adapter = self.adapter or CodexCliAdapter(status.cli_status)
        event_ids.append(self._event(run, "codex_run_planning", "Planejamento publico", "Vou chamar o Codex CLI com historico sanitizado e sem expor tokens.").event_id)
        self._publish("codex_agent_message_sent", "Prompt enviado ao Codex Agent.", {"session_id": request.session_id, "operation_type": request.operation_type})
        result = adapter.run_prompt(
            prompt=self._prompt_with_history(request.session_id, request.prompt, config),
            config=config,
            workdir=request.workspace_context or config.default_workdir,
        )
        event_ids.append(self._event(run, "codex_explanation", "Resposta recebida", "Codex retornou uma resposta sanitizada para a sessao mobile.", payload={"cli_status": result.cli_status, "latency_ms": result.latency_ms, "event_count": result.event_count}, status=result.status).event_id)
        tool_results = self._execute_tool_requests(run, kernel_run, request, adapter_text=result.text)
        for item in tool_results:
            event_ids.extend(item.get("codex_event_ids", []))
        artifact_ids = [
            artifact_id
            for item in tool_results
            for artifact_id in item.get("artifact_ids", [])
        ]
        tool_blocked = any(item.get("status") in {"blocked", "approval_required"} for item in tool_results)
        tool_failed = any(item.get("status") == "failed" for item in tool_results)
        validation_status = "passed" if result.status == "completed" else "not_started"
        if tool_results:
            validation_status = "passed" if not (tool_blocked or tool_failed) else "not_started"
        if autoreview_enabled:
            event_ids.append(self._event(run, "codex_run_autoreview_started", "Auto review iniciado", "Vou revisar se o estado final combina com o que foi executado.").event_id)
            event_ids.append(
                self._event(
                    run,
                    "codex_run_autoreview_finished",
                    "Auto review concluido",
                    self._autoreview_message(result.status, validation_status, tool_results=tool_results),
                    payload={"tool_results": tool_results, "artifact_ids": artifact_ids},
                    status=result.status,
                ).event_id
            )
        final_status = result.status if result.status in {"completed", "blocked", "failed"} else ("completed" if result.status == "completed" else result.status)
        if tool_failed:
            final_status = "failed"
        elif tool_blocked:
            final_status = "blocked"
        elif tool_results and result.status == "completed":
            final_status = "completed"
        response = CodexAgentResponse(
            session_id=request.session_id,
            run_id=run.run_id,
            status=final_status,
            text=self._final_text(result.text, tool_results)[: request.max_output_chars or config.max_output_chars],
            cli_status=result.cli_status,
            latency_ms=result.latency_ms,
            cli_event_count=result.event_count,
            error_code=result.error_code,
            human_error="Codex CLI nao executou a solicitacao." if result.status in {"failed", "blocked"} else None,
            structured_actions=self._actions(request, policy),
            event_ids=event_ids,
            artifact_ids=artifact_ids,
            validation_status=validation_status,
        )
        final_message = self._store_response(response, policy, run_id=run.run_id)
        response = response.model_copy(update={"final_message_id": final_message.message_id})
        run_status = "completed" if response.status == "completed" else response.status
        self.store.update_run(run.run_id, status=run_status, completed_at=utc_now_iso(), validation_status=validation_status, final_message_id=final_message.message_id, error_code=response.error_code)
        if artifact_ids:
            self.store.update_run(run.run_id, artifact_ids=artifact_ids)
        event_ids.append(self._event(run, "codex_run_completed" if response.status == "completed" else "codex_run_failed", "Run finalizado", "Execucao Codex finalizada com estado confirmado.", status=response.status, severity="info" if response.status == "completed" else "warning").event_id)
        self._create_memory_candidate(run, response, tool_results)
        response = response.model_copy(update={"event_ids": event_ids})
        self._publish("codex_agent_response_received", "Resposta Codex Agent registrada.", {"operation_id": response.operation_id, "status": response.status, "cli_status": response.cli_status}, status=response.status)
        if response.status == "completed":
            self._publish("codex_agent_completed", "Codex Agent concluiu sem bypass de side effects.", {"operation_id": response.operation_id}, status="completed")
        return response

    def _direct_write_lock_decision(self, request: CodexAgentRequest, run_id: str):
        if not request.workspace_context:
            return None
        write_capabilities = set(self.hybrid_policy.codex().get("write_capabilities", []))
        if not (set(request.requested_capabilities) & write_capabilities):
            return None
        target_paths = [tool.path_ref for tool in request.tool_requests if tool.path_ref] or [request.workspace_context]
        return self.workspace_locks.check_write_conflict(
            WriteConflictCheckRequest(
                workspace=request.workspace_context,
                actor_agent="codex",
                owner_task_id=run_id,
                target_paths=target_paths,
                operation_type=request.operation_type,
            )
        )

    def _effective_tool_requests(self, request: CodexAgentRequest, adapter_text: str = "") -> list[CodexToolRequest]:
        if request.tool_requests:
            return request.tool_requests
        if "create_file" not in set(request.requested_capabilities or []):
            return []
        filename = self._extract_requested_filename(request.prompt)
        if not filename or not request.workspace_context:
            return []
        workspace_id = self._infer_workspace_id(request.workspace_context)
        content = self._content_for_requested_file(request.prompt, adapter_text)
        return [
            CodexToolRequest(
                tool_name="create_file",
                workspace_id=workspace_id,
                path_ref=str(Path(request.workspace_context) / filename),
                operation_type="create_file",
                input={
                    "content": content,
                    "overwrite": True,
                },
                metadata_sanitized={
                    "source": "codex_agent_governed_action_planner",
                    "planner_mode": "explicit_create_file_request",
                },
            )
        ]

    def _extract_requested_filename(self, prompt: str) -> str | None:
        return self.local_action_planner.extract_requested_filename(prompt)

    def _infer_workspace_id(self, workspace_context: str) -> str | None:
        return self.local_action_planner.infer_workspace_id(workspace_context)

    def _content_for_requested_file(self, prompt: str, adapter_text: str) -> str:
        return self.local_action_planner.content_for_requested_file(prompt, adapter_text)

    def _looks_like_failed_file_content(self, text: str) -> bool:
        return self.local_action_planner.looks_like_failed_content(text)

    def _create_kernel_run(self, run: CodexRun, request: CodexAgentRequest):
        session = self.agent_kernel.create_session(
            "codex",
            AgentSessionCreateRequest(
                title=f"Codex bridge {run.run_id[-8:]}",
                metadata_sanitized={
                    "codex_session_id": request.session_id,
                    "codex_run_id": run.run_id,
                    "bridge": "codex_agent_tool_gateway",
                },
            ),
        )
        kernel_run = self.agent_kernel.create_run(
            "codex",
            session.session_id,
            AgentRunCreateRequest(
                operation_type=request.operation_type,
                status="running",
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={
                    "codex_session_id": request.session_id,
                    "codex_run_id": run.run_id,
                    "workspace_context": request.workspace_context,
                },
            ),
        )
        return session, kernel_run

    def _load_memory_context(self, run: CodexRun, kernel_run) -> tuple[list[str], list[str]]:
        try:
            context = self.memory_gateway.load_context_for_run(
                MemoryContextLoadRequest(
                    agent_id="codex",
                    session_id=kernel_run.session_id,
                    run_id=kernel_run.run_id,
                    limit=10,
                    max_chars=16000,
                    reason="codex_agent_run_start",
                )
            )
            return context.memory_refs_used, context.warnings
        except Exception as exc:
            return [], [f"memory_context_load_failed:{type(exc).__name__}"]

    def _execute_tool_requests(self, run: CodexRun, kernel_run, request: CodexAgentRequest, *, adapter_text: str = "") -> list[dict[str, Any]]:
        tool_requests = self._effective_tool_requests(request, adapter_text=adapter_text)
        if not tool_requests:
            return []
        results: list[dict[str, Any]] = []
        max_steps = self.config_service.runtime().autorun_max_steps
        for index, tool_request in enumerate(tool_requests[:max_steps], start=1):
            requested_event = self._event(
                run,
                "codex_tool_requested",
                "Tool solicitada",
                f"Codex solicitou a ferramenta governada {tool_request.tool_name}.",
                payload={"tool_name": tool_request.tool_name, "sequence": index},
                status="requested",
            )
            try:
                result = self.tool_gateway.invoke(
                    "codex",
                    kernel_run.run_id,
                    tool_request.tool_name,
                    ToolInvocationCreateRequest(
                        operation_type=tool_request.operation_type or tool_request.tool_name,
                        workspace_id=tool_request.workspace_id,
                        path_ref=tool_request.path_ref,
                        input=tool_request.input,
                        metadata_sanitized={
                            **tool_request.metadata_sanitized,
                            "execution_mode": run.autopilot_mode,
                            "codex_run_id": run.run_id,
                        },
                    ),
                )
            except Exception as exc:
                failed = self._event(
                    run,
                    "codex_tool_failed",
                    "Tool falhou",
                    "A ferramenta governada falhou de forma controlada.",
                    payload={"tool_name": tool_request.tool_name, "error_type": type(exc).__name__},
                    severity="error",
                    status="failed",
                )
                results.append(
                    {
                        "tool_name": tool_request.tool_name,
                        "status": "failed",
                        "artifact_ids": [],
                        "codex_event_ids": [requested_event.event_id, failed.event_id],
                        "error_code": type(exc).__name__,
                    }
                )
                continue
            results.append(self._mirror_tool_result(run, result, requested_event.event_id))
        if len(tool_requests) > max_steps:
            limit_event = self._event(
                run,
                "codex_run_completed_with_warnings",
                "Limite de autorun atingido",
                "Nem todas as ferramentas foram executadas porque o limite configurado de steps foi atingido.",
                payload={"requested": len(tool_requests), "executed": max_steps},
                severity="warning",
                status="completed_with_warnings",
            )
            results.append({"tool_name": "autorun_limit", "status": "completed_with_warnings", "artifact_ids": [], "codex_event_ids": [limit_event.event_id]})
        return results

    def _mirror_tool_result(self, run: CodexRun, result: ToolInvocationResult, requested_event_id: str) -> dict[str, Any]:
        invocation = result.tool_invocation
        artifact_ids = [artifact.artifact_id for artifact in result.artifacts]
        for artifact in result.artifacts:
            self.store.add_artifact(
                CodexArtifact(
                    artifact_id=artifact.artifact_id,
                    session_id=run.session_id,
                    run_id=run.run_id,
                    filename=artifact.filename,
                    content_type=artifact.content_type,
                    size=artifact.size,
                    origin=f"tool_gateway:{artifact.origin}",
                    backend_ref=artifact.artifact_id,
                    download_endpoint=artifact.download_endpoint,
                    metadata={"tool_invocation_id": invocation.tool_invocation_id},
                )
            )
        status_event = {
            "succeeded": "codex_tool_succeeded",
            "blocked": "codex_tool_blocked",
            "approval_required": "codex_tool_approval_required",
            "failed": "codex_tool_failed",
        }.get(result.status, "codex_tool_finished")
        human = {
            "succeeded": "Ferramenta governada concluida.",
            "blocked": "Ferramenta governada bloqueada por policy.",
            "approval_required": "Ferramenta governada exige approval.",
            "failed": "Ferramenta governada falhou.",
        }.get(result.status, "Ferramenta governada finalizada.")
        event = self._event(
            run,
            status_event,
            "Tool Gateway",
            human,
            payload={
                "tool_invocation_id": invocation.tool_invocation_id,
                "tool_name": invocation.tool_name,
                "status": result.status,
                "policy_decision_id": invocation.policy_decision_id,
                "block_reason_code": invocation.block_reason_code,
                "artifact_ids": artifact_ids,
                "output": result.output,
            },
            severity="warning" if result.status in {"blocked", "approval_required"} else ("error" if result.status == "failed" else "info"),
            status=result.status,
        )
        if result.validation_result is not None:
            validation_event = self._event(
                run,
                "codex_validation_passed" if result.validation_result.status == "passed" else "codex_validation_failed",
                "Validation",
                f"Validation {result.validation_result.status}.",
                payload=result.validation_result.model_dump(),
                status=result.validation_result.status,
                severity="info" if result.validation_result.status == "passed" else "warning",
            )
            event_ids = [requested_event_id, event.event_id, validation_event.event_id]
        else:
            event_ids = [requested_event_id, event.event_id]
        return {
            "tool_name": invocation.tool_name,
            "tool_invocation_id": invocation.tool_invocation_id,
            "status": result.status,
            "artifact_ids": artifact_ids,
            "codex_event_ids": event_ids,
            "policy_decision_id": invocation.policy_decision_id,
            "block_reason_code": invocation.block_reason_code,
            "output_summary": invocation.output_summary_sanitized,
        }

    def _final_text(self, adapter_text: str, tool_results: list[dict[str, Any]]) -> str:
        if not tool_results:
            return adapter_text
        successful_tools = [item for item in tool_results if item.get("status") == "succeeded"]
        failed_adapter_text = self._looks_like_failed_file_content(adapter_text)
        if successful_tools and failed_adapter_text:
            lines = [
                "A execução governada concluiu a ação solicitada. A resposta textual do adaptador indicou limitação do sandbox, mas o Tool Gateway autorizado executou a etapa com validação.",
                "",
                "Acoes governadas executadas:",
            ]
        else:
            lines = [adapter_text.strip(), "", "Acoes governadas executadas:"]
        for item in tool_results:
            lines.append(f"- {item.get('tool_name')}: {item.get('status')}")
            if item.get("output_summary"):
                lines.append(f"  - {item.get('output_summary')}")
            for artifact_id in item.get("artifact_ids", []):
                lines.append(f"  - artifact_id: {artifact_id}")
        return "\n".join(line for line in lines if line is not None).strip()

    def _create_memory_candidate(self, run: CodexRun, response: CodexAgentResponse, tool_results: list[dict[str, Any]]) -> None:
        if not tool_results and response.status != "completed":
            return
        try:
            candidate = self.memory_gateway.create_candidate(
                MemoryCandidateCreateRequest(
                    proposed_by_agent_id="codex",
                    namespace="memory:codex",
                    scope="private",
                    title=f"Codex run {response.status}",
                    content_sanitized=(
                        "Run Codex finalizado com status "
                        f"{response.status}. Tools: "
                        + ", ".join(f"{item.get('tool_name')}={item.get('status')}" for item in tool_results)
                    )[:2000],
                    memory_type="workflow_lesson",
                    source_ref=f"codex_run:{run.run_id}",
                    evidence_refs=[f"codex_run:{run.run_id}", *(f"artifact:{artifact_id}" for artifact_id in response.artifact_ids)],
                    confidence="medium",
                    reason_to_remember="codex_agent_run_summary",
                    session_id=run.session_id,
                    run_id=str(run.metadata.get("agent_kernel_run_id") or ""),
                    metadata_sanitized={"codex_run_id": run.run_id, "status": response.status},
                )
            )
            self._event(
                run,
                "codex_memory_candidate_created",
                "Memory candidate criado",
                "Codex criou um candidato de memoria privado a partir do resultado da execucao.",
                payload={"candidate_id": candidate.candidate_id},
                status="created",
            )
        except Exception as exc:
            self._event(
                run,
                "codex_memory_warning",
                "Memory candidate nao criado",
                "A execucao continuou, mas a memoria candidata nao foi gravada.",
                payload={"error_type": type(exc).__name__},
                severity="warning",
                status="warning",
            )

    def _prompt_with_history(self, session_id: str, current_prompt: str, config: Any) -> str:
        messages = self.store.messages(session_id)
        prior = messages[:-1][-config.history_context_messages :]
        if not prior:
            return current_prompt
        transcript = "\n\n".join(f"{message.role}: {message.content}" for message in prior)
        if len(transcript) > config.history_context_chars:
            transcript = transcript[-config.history_context_chars :]
        return (
            "Continue a conversa persistida abaixo. Trate o ultimo pedido como a instrucao atual. "
            "Nao execute efeitos colaterais: esta chamada opera em sandbox read-only.\n\n"
            f"HISTORICO SANITIZADO:\n{transcript}\n\nPEDIDO ATUAL:\n{current_prompt}"
        )

    def guarded_action(self, session_id: str, action: str) -> dict[str, object]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        payload = {"status": "blocked", "agent_id": "codex_agent", "action": action, "reason": "governed_pipeline_required"}
        self._publish("codex_agent_blocked", "Acao Codex bloqueada ate existir approval/pipeline governado valido.", payload, severity="warning", status="blocked")
        return payload

    def cancel_run(self, run_id: str) -> dict[str, object]:
        run = self.store.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        if run.status in {"completed", "completed_with_warnings", "validation_failed", "blocked", "failed", "cancelled"}:
            return {"status": "ok", "run": run.model_dump(), "already_terminal": True}
        event = self._event(run, "codex_run_cancelled", "Run cancelado", "Cancelamento solicitado pelo mobile; nenhuma nova etapa sera iniciada.", status="cancelled", severity="warning")
        updated = self.store.update_run(run_id, status="cancelled", completed_at=utc_now_iso(), error_code="cancelled_by_user")
        self.store.add_message(CodexChatMessage(session_id=run.session_id, role="codex", content="Run Codex cancelado pelo usuario.", run_id=run_id, event_id=event.event_id, message_kind="cancelled"))
        return {"status": "ok", "run": (updated or run).model_dump(), "event": event.model_dump()}

    def artifacts(self, session_id: str) -> list[CodexArtifact]:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        return self.store.artifacts(session_id=session_id)

    def attach_uploaded_artifact(self, *, session_id: str, filename: str, content: bytes, content_type: str = "application/octet-stream", run_id: str | None = None) -> CodexArtifact:
        if self.store.get(session_id) is None:
            raise FileNotFoundError(session_id)
        config = self.config_service.runtime()
        if not config.allow_artifact_upload:
            raise PermissionError("codex_artifact_upload_disabled")
        upload = ArtifactUploadService().upload(
            ArtifactUploadRequest(
                filename=filename,
                content=base64.b64encode(content).decode("ascii"),
                encoding="base64",
                content_type=content_type,
                metadata={"agent_id": "codex_agent", "session_id": session_id, "run_id": run_id, "origin": "mobile_upload"},
            )
        )
        artifact = CodexArtifact(
            artifact_id=upload.artifact.artifact_id,
            session_id=session_id,
            run_id=run_id,
            filename=upload.artifact.filename,
            content_type=upload.artifact.content_type,
            size=upload.artifact.size_bytes,
            origin="mobile_upload",
            backend_ref=upload.artifact.storage_path,
            download_endpoint=upload.download_path,
        )
        self.store.add_artifact(artifact)
        run = self.store.get_run(run_id) if run_id else self.store.latest_run(session_id)
        if run:
            self._event(run, "codex_artifact_uploaded", "Artifact anexado", f"Upload concluido: {artifact.filename}", payload=artifact.model_dump())
            self.store.update_run(run.run_id, artifact_ids=sorted(set([*run.artifact_ids, artifact.artifact_id])))
        self.store.add_message(CodexChatMessage(session_id=session_id, role="codex", content=f"Artifact anexado: {artifact.filename}", run_id=run_id, message_kind="artifact_uploaded", metadata={"artifact_id": artifact.artifact_id}))
        return artifact

    def artifact_download_path(self, artifact_id: str) -> Path:
        artifact = self.store.get_artifact(artifact_id)
        if artifact is None:
            raise FileNotFoundError(artifact_id)
        return ArtifactDownloadService().path(artifact_id)

    def mobile_view_model(self, session_id: str, *, after_event_id: str | None = None) -> dict[str, object]:
        session = self.store.get(session_id)
        if session is None:
            raise FileNotFoundError(session_id)
        run = self.store.latest_run(session_id)
        events = self.store.events(run.run_id, after_event_id=after_event_id, limit=self.config_service.runtime().max_events_per_poll) if run else []
        return {
            "status": "ok",
            "agent_id": "codex_agent",
            "session": session.model_dump(),
            "active_run": run.model_dump() if run else None,
            "polling": {"interval_seconds": self.config_service.runtime().polling_interval_seconds, "after_event_id": after_event_id},
            "events": [event.model_dump() for event in events if event.visible_in_mobile],
            "messages": [message.model_dump() for message in self.store.messages(session_id) if message.visible_in_mobile],
            "artifacts": [artifact.model_dump() for artifact in self.store.artifacts(session_id=session_id)],
            "raw_default_visible": False,
            "token_in_url": False,
        }

    def _actions(self, request: CodexAgentRequest, policy: dict[str, Any]) -> list[dict[str, Any]]:
        actions = []
        for capability in request.requested_capabilities:
            if capability in {"create_patch_preview", "apply_approved_patch", "workspace_write", "shell", "run_approved_shell"}:
                actions.append({"action_type": capability, "status": "pending_approval" if policy.get("requires_approval") else "preview_only", "requires_approval": bool(policy.get("requires_approval")), "validation_required": True, "policy_decision": policy})
        return actions

    def _store_response(self, response: CodexAgentResponse, policy: dict[str, Any], *, run_id: str | None = None) -> CodexChatMessage:
        return self.store.add_message(CodexChatMessage(session_id=response.session_id, role="codex", content=response.text, run_id=run_id, operation_id=response.operation_id, message_kind="final_answer", metadata={"status": response.status, "policy_decision": redact_payload(policy), "validation_status": response.validation_status}))

    def _event(
        self,
        run: CodexRun,
        event_type: str,
        title: str,
        human_message: str,
        *,
        payload: dict[str, Any] | None = None,
        severity: str = "info",
        status: str = "info",
    ) -> CodexRunEvent:
        event = self.store.add_event(
            CodexRunEvent(
                run_id=run.run_id,
                session_id=run.session_id,
                event_type=event_type,
                title=title,
                human_message=human_message,
                technical_summary_sanitized=human_message,
                payload_sanitized=redact_payload(payload or {}),
                severity=severity,
                status=status,
            )
        )
        return event

    def _policy_message(self, policy: dict[str, Any]) -> str:
        if policy.get("allowed"):
            return "Policy permitiu a solicitacao dentro das capacidades declaradas."
        reasons = ", ".join(str(item) for item in policy.get("reasons", []) or ["policy_block"])
        return f"Policy bloqueou a solicitacao: {reasons}."

    def _autoapproval_decisions(self, run: CodexRun, request: CodexAgentRequest, policy: dict[str, Any]) -> list[CodexAutoApprovalDecision]:
        config = self.config_service.runtime()
        if not run.autoapproval_enabled:
            return []
        decisions: list[CodexAutoApprovalDecision] = []
        workspace = (policy.get("workspace") or {}) if isinstance(policy.get("workspace"), dict) else {}
        contract = workspace.get("contract") or {}
        workspace_role = contract.get("role") or workspace.get("role")
        workspace_id = contract.get("workspace_id") or workspace.get("workspace_id")
        for capability in request.requested_capabilities or ["codex_chat"]:
            approved, reason, risk = self._autoapproval_for(capability, workspace_role, config, policy)
            decisions.append(
                CodexAutoApprovalDecision(
                    run_id=run.run_id,
                    session_id=run.session_id,
                    action_type=capability,
                    capability=capability,
                    workspace_id=workspace_id,
                    workspace_role=workspace_role,
                    risk_level=risk,
                    reason=reason,
                    approved=approved,
                    evidence_refs=[run.run_id],
                )
            )
        return decisions

    def _autoapproval_for(self, capability: str, workspace_role: str | None, config: Any, policy: dict[str, Any]) -> tuple[bool, str, str]:
        if not policy.get("allowed"):
            return False, "Auto approval negado porque a policy principal bloqueou a solicitacao.", "high"
        if capability in {"codex_chat", "read_workspace", "scan_workspace"}:
            return bool(config.auto_approve_read), "Auto approval aplicado: leitura permitida em workspace autorizado.", "low"
        if capability in {"workspace_write", "create_patch_preview"}:
            allowed = bool(config.auto_approve_write_in_target_mutable and workspace_role in {"target_mutable", "system_mutable"})
            return allowed, "Auto approval aplicado para escrita governada em workspace mutavel." if allowed else "Auto approval negado: escrita fora de workspace mutavel.", "medium"
        if capability in {"shell", "run_approved_shell"}:
            return bool(config.auto_approve_test_shell), "Auto approval aplicado: shell de teste/build permitido pela policy; shell destrutivo continua bloqueado.", "medium"
        return False, f"Auto approval negado: capability desconhecida ou nao permitida ({capability}).", "high"

    def _autoreview_message(self, status: str, validation_status: str, *, tool_results: list[dict[str, Any]] | None = None) -> str:
        tool_results = tool_results or []
        blocked = [item for item in tool_results if item.get("status") in {"blocked", "approval_required"}]
        failed = [item for item in tool_results if item.get("status") == "failed"]
        if failed:
            return "Auto review detectou falha em ferramenta governada; a execucao nao deve ser tratada como concluida."
        if blocked:
            return "Auto review detectou ferramenta bloqueada ou pendente de approval; a execucao permanece governada."
        if status == "completed" and validation_status == "passed":
            return "Auto review confirmou que ha resposta final e nenhum side effect foi declarado sem validacao."
        return "Auto review manteve o resultado como nao concluido ou pendente porque o estado final nao passou completamente."

    def _publish(self, event_type: str, summary: str, payload: dict[str, Any], *, severity: str = "info", status: str = "created") -> None:
        try:
            EventPublisherService().publish(EventPublishRequest(event_type=event_type, source_service="codex_agent", human_summary=summary, payload=redact_payload(payload), severity=severity, status=status, visibility="public", copy_policy="copy_sanitized"))
        except ValueError:
            return
