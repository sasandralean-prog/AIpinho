from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.schemas.chat.chat_trace import ChatTraceItem
from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.schemas.policy.policy_decision import PolicyDecision
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.chat.chat_context_builder import ChatContextBuilder
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.chat.governed_write_chat_service import GovernedWriteChatService
from aipinho.services.chat.artifact_request_preview_service import ArtifactRequestPreviewService
from aipinho.services.chat.chat_artifact_fulfillment_service import ChatArtifactFulfillmentService
from aipinho.services.chat.chat_manual_inference_service import ChatManualInferenceService
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService
from aipinho.services.chat.chat_operation_router_service import ChatOperationRouterService
from aipinho.services.chat.chat_permission_grant_service import ChatPermissionGrantService
from aipinho.services.chat.permission_status_response_service import PermissionStatusResponseService
from aipinho.services.chat.workspace_metadata_query_service import WorkspaceMetadataQueryService
from aipinho.services.chat.chat_response_policy_service import ChatResponsePolicyService
from aipinho.services.debugger.decision_trace_service import DecisionTraceService
from aipinho.services.interpreter.interpreter_service import InterpreterService
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.governance.operation_contract_service import OperationContractService
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.reports.project_report_service import ProjectReportService
from aipinho.services.roles.role_model_status_service import RoleModelStatusService
from aipinho.services.roles.role_pipeline_service import RolePipelineService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.services.models.manual_inference_status_service import ManualInferenceStatusService
from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService
from aipinho.services.models.model_invocation_service import ModelInvocationService
from aipinho.services.models.model_status_service import ModelStatusService
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService
from aipinho.services.rag.integration.context_prompt_policy_service import ContextPromptPolicyService
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.services.session.session_service import SessionService
from aipinho.services.session.session_store import utc_now
from aipinho.services.speaker.anti_truncation_service import AntiTruncationService
from aipinho.services.speaker.speaker_service import SpeakerService
from aipinho.services.sandbox_file_writer_service import SandboxFileWriterService
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService
from aipinho.services.web_search_provider_service import WebSearchProviderService
from aipinho.services.web_search_summary_service import WebSearchSummaryService
from aipinho.utils.yaml_loader import load_yaml_file


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _to_list(values: list[Any]) -> list[dict[str, Any]]:
    return [_to_dict(value) for value in values]


class ChatService:
    DIRECT_INTENTS = {"conversation", "self_analysis", "capability_explanation", "in_chat_final_report"}

    def __init__(
        self,
        prompt_intelligence: PromptIntelligenceService | None = None,
        policy_decisions: EffectivePolicyDecisionService | None = None,
        policy_kernel: Any | None = None,
        response_policy: ChatResponsePolicyService | None = None,
        speaker: SpeakerService | None = None,
        interpreter: InterpreterService | None = None,
        trace_service: DecisionTraceService | None = None,
        session_service: SessionService | None = None,
        task_draft_service: TaskContractDraftService | None = None,
        task_preview_service: TaskPreviewService | None = None,
        approval_service: ApprovalService | None = None,
        prompt_assembly_service: PromptAssemblyService | None = None,
        model_invocation_service: ModelInvocationService | None = None,
        task_runtime_service: TaskRuntimeService | None = None,
        governed_write_service: GovernedWriteChatService | None = None,
        web_search_provider: WebSearchProviderService | None = None,
        sandbox_writer: SandboxFileWriterService | None = None,
        operation_contract_service: OperationContractService | None = None,
        permission_grant_service: ChatPermissionGrantService | None = None,
        context_prompt_policy: ContextPromptPolicyService | None = None,
    ) -> None:
        self.prompt_intelligence = prompt_intelligence or PromptIntelligenceService()
        self.policy_decisions = policy_decisions or EffectivePolicyDecisionService(legacy_policy_kernel=policy_kernel)
        self.response_policy = response_policy or ChatResponsePolicyService().load()
        self.interpreter = interpreter or InterpreterService()
        self.speaker = speaker or SpeakerService(interpreter=self.interpreter)
        self.trace_service = trace_service or DecisionTraceService()
        self.context_builder = ChatContextBuilder()
        self.session_service = session_service or SessionService()
        self.task_draft_service = task_draft_service or TaskContractDraftService()
        self.task_preview_service = task_preview_service or TaskPreviewService()
        self.approval_service = approval_service or ApprovalService(
            preview_service=self.task_preview_service,
            draft_store=self.task_draft_service.store,
        )
        self.prompt_assembly_service = prompt_assembly_service or PromptAssemblyService()
        self.model_invocation_service = model_invocation_service or ModelInvocationService()
        self.task_runtime_service = task_runtime_service or TaskRuntimeService(
            drafts=self.task_draft_service,
            previews=self.task_preview_service,
            approvals=self.approval_service,
        )
        self.governed_write_service = governed_write_service or GovernedWriteChatService()
        self.web_search_provider = web_search_provider or WebSearchProviderService()
        self.sandbox_writer = sandbox_writer or SandboxFileWriterService()
        self.operation_contract_service = operation_contract_service or OperationContractService()
        self.permission_grant_service = permission_grant_service or ChatPermissionGrantService(operation_contracts=self.operation_contract_service)
        self.context_prompt_policy = context_prompt_policy or ContextPromptPolicyService()
        self.chat_model_policy = ChatModelPolicyService()
        self.read_only_execution_policy = load_yaml_file(PATHS.config_root / "policies" / "read_only_execution_policy.yaml", critical=True, root=PATHS.config_root / "policies")

    def respond(self, request: ChatRequest) -> ChatResponse:
        session_state = self.session_service.ensure_session(request)
        if request.context and request.context.active_task_id and self._requests_task_status(request.message):
            existing_run = self.task_runtime_service.get_run(request.context.active_task_id)
            if existing_run is not None:
                existing_result = self.task_runtime_service.get_result(existing_run.run_id)
                result_summary = existing_result.summary if existing_result is not None else "Resultado final ainda nao disponivel."
                validation = existing_result.validation if existing_result is not None else None
                validation_note = "Validacao ainda nao disponivel."
                if isinstance(validation, dict):
                    validation_status = validation.get("status", "unknown")
                    if validation_status in {"passed", "passed_with_warnings"}:
                        validation_note = f"Validacao: {validation_status}."
                    elif validation_status in {"failed", "rejected"}:
                        validation_note = f"Validacao: {validation_status}; resultado nao deve ser tratado como confiavel."
                    else:
                        validation_note = f"Validacao: {validation_status}; revise limitacoes antes de confiar."
                return ChatResponse(
                    response_id=f"chat_{uuid4().hex}",
                    session_id=session_state.session_id,
                    status="ok",
                    message=f"TaskRun {existing_run.run_id}: status {existing_run.status}. {validation_note} {result_summary}",
                    next_actions=[
                        ChatNextAction(type="view_task_run", label="Ver TaskRun", target_id=existing_run.run_id),
                        ChatNextAction(type="cancel_task_run", label="Cancelar TaskRun", target_id=existing_run.run_id),
                    ] if existing_run.status in {"created", "queued", "running", "waiting_input"} else [ChatNextAction(type="view_task_run", label="Ver TaskRun", target_id=existing_run.run_id)],
                    warnings=[],
                )
        if not request.message.strip():
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="error",
                message="Mensagem vazia. Envie um texto para eu analisar com seguranca.",
                warnings=["empty_message"],
                trace=[],
            )
        approval_command_response = ChatApprovalCommandService(approvals=self.approval_service).handle(
            session_state.session_id,
            request.message,
            source_channel=(request.context.surface if request.context and request.context.surface else "api"),
        )
        if approval_command_response is not None:
            return approval_command_response
        grant_response = self.permission_grant_service.handle(
            session_id=session_state.session_id,
            text=request.message,
            source_channel=(request.context.surface if request.context and request.context.surface else "api"),
            active_workspace=(request.context.active_workspace if request.context else None),
        )
        if grant_response is not None:
            return grant_response
        context_policy_decision = self.context_prompt_policy.evaluate_user_message(request.message)
        if not context_policy_decision.allowed:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="blocked",
                operation_type="context_prompt_policy",
                message_type="blocked_policy_message",
                message=context_policy_decision.message,
                intent={
                    "intent_type": "conversation",
                    "operation_type": "context_prompt_policy",
                    "requires_task": False,
                },
                policy={
                    "permission": "denied",
                    "reason_code": context_policy_decision.reason_code,
                    "context_prompt_policy": {
                        "allowed": context_policy_decision.allowed,
                        "evidence": context_policy_decision.evidence,
                    },
                },
                warnings=context_policy_decision.warnings,
            )
        operation_decision = ChatOperationRouterService().route(
            request.message,
            workspace_hint=(request.context.active_workspace if request.context else None),
        )
        if operation_decision.operation_type == "product_planning_readonly":
            return self._product_planning_readonly_response(session_state.session_id, operation_decision)
        if operation_decision.operation_type == "workspace_permission_list":
            return PermissionStatusResponseService().respond(
                session_id=session_state.session_id,
                operation_id=operation_decision.operation_id,
                operation_type="workspace_permission_list",
            )
        if operation_decision.operation_type == "permission_status":
            return PermissionStatusResponseService().respond(
                session_id=session_state.session_id,
                operation_id=operation_decision.operation_id,
            )
        if operation_decision.operation_type == "workspace_metadata_query":
            return WorkspaceMetadataQueryService().respond(
                session_id=session_state.session_id,
                decision=operation_decision,
            )
        if operation_decision.operation_type == "public_fact_query":
            return self._public_fact_query_response(session_state.session_id, operation_decision)
        if operation_decision.operation_type == "dangerous_operation_blocked":
            return self._blocked_operation_response(session_state.session_id, operation_decision)
        if operation_decision.operation_type == "attachment_required_missing":
            return self._attachment_required_missing_response(session_state.session_id, operation_decision)
        if operation_decision.operation_type == "filesystem_archive_request":
            return ChatArtifactFulfillmentService().fulfill_filesystem_archive(session_id=session_state.session_id, decision=operation_decision)
        if operation_decision.operation_type == "artifact_request":
            factual_response = None
            if operation_decision.primary_prompt and operation_decision.primary_prompt.strip() and operation_decision.primary_prompt.strip() != request.message.strip():
                factual_response = self.respond(
                    ChatRequest(
                        message=operation_decision.primary_prompt,
                        session_id=session_state.session_id,
                        mode="normal",
                        include_trace=False,
                        context=request.context,
                    )
                )
            if factual_response is not None and factual_response.status == "ok" and factual_response.message.strip():
                return ChatArtifactFulfillmentService().fulfill_response_artifact(
                    session_id=session_state.session_id,
                    decision=operation_decision,
                    factual_response=factual_response,
                )
            return ArtifactRequestPreviewService().offer(operation_decision, factual_response)
        if operation_decision.operation_type == "readonly_analysis_with_artifact_output":
            return ChatArtifactFulfillmentService().fulfill_readonly_analysis(
                session_id=session_state.session_id,
                prompt=request.message,
                decision=operation_decision,
            )
        governed_write_response = self.governed_write_service.from_decision(
            session_id=session_state.session_id,
            prompt=request.message,
            decision=operation_decision,
            workspace_ref=(request.context.active_workspace if request.context else None) or operation_decision.workspace,
            execution_mode="governed_autorun",
        )
        if governed_write_response is not None:
            if governed_write_response.status == "pending_approval" and not governed_write_response.approval_id:
                governed_write_response = self._governed_write_approval_response(
                    session_state.session_id,
                    request.message,
                    operation_decision,
                    workspace_ref=(request.context.active_workspace if request.context else None) or operation_decision.workspace,
                    base_response=governed_write_response,
                )
            self.session_service.update_after_chat(
                session_state,
                request,
                None,
                None,
                task_draft_id=governed_write_response.task_id,
                status=governed_write_response.status,
            )
            return governed_write_response
        if str(operation_decision.metadata.get("router_operation_type") or "") == "governed_shell_request":
            return self._governed_shell_preview_response(
                session_state.session_id,
                request.message,
                operation_decision,
                workspace_ref=(request.context.active_workspace if request.context else None) or operation_decision.workspace,
            )
        if operation_decision.operation_type in {"filesystem_write_file", "filesystem_create_directory", "filesystem_read_file", "filesystem_append_file", "sandbox_capability_test", "sandbox_batch_artifact_request"}:
            sandbox_response = self._sandbox_writer_response(session_state.session_id, request.message, operation_decision)
            if sandbox_response is not None:
                self.session_service.update_after_chat(
                    session_state,
                    request,
                    None,
                    None,
                    task_draft_id=sandbox_response.task_id,
                    status=sandbox_response.status,
                )
                if sandbox_response.status == "ready" and sandbox_response.policy.get("path"):
                    self.session_service.record_operational_context(
                        session_state.session_id,
                        {
                            "operation_type": sandbox_response.operation_type,
                            "path": sandbox_response.policy.get("path"),
                            "run_id": sandbox_response.task_id,
                        },
                    )
                return sandbox_response
            return self._specific_operation_preview_response(session_state.session_id, operation_decision)
        if (
            operation_decision.operation_type in {"project_create", "android_project_create", "project_generation", "governed_project_rebuild", "logforge_mobile_implementation", "android_apk_build", "artifact_build_request"}
            or str(operation_decision.metadata.get("router_operation_type") or "") in {"project_create", "android_project_create", "governed_project_rebuild", "project_bootstrap"}
        ):
            return self._specific_operation_preview_response(session_state.session_id, operation_decision)
        if (
            operation_decision.operation_type == "project_analysis"
            and operation_decision.metadata.get("router_operation_type") == "readonly_project_analysis"
        ):
            return self._readonly_project_analysis_preview_response(
                session_state.session_id,
                operation_decision,
                workspace_ref=(request.context.active_workspace if request.context else None) or operation_decision.workspace,
            )
        if self._requests_role_model_status(request.message):
            return self._role_model_status_response(session_state.session_id)
        if self._requests_role_model_14b(request.message):
            return self._role_model_14b_block_response(session_state.session_id)
        if self._requests_role_model_run(request.message):
            return self._role_model_run_guidance_response(request.message, session_state.session_id)
        if self._requests_model_catalog(request.message):
            return self._model_catalog_response(session_state.session_id)
        if self._requests_debugger_mutation(request.message):
            return self._debugger_read_only_block_response(session_state.session_id)
        if self._requests_raw_debug_prompt(request.message):
            return self._raw_debug_block_response(session_state.session_id)
        if self._requests_debugger_blocked_reason(request.message):
            return self._debugger_blocked_reason_response(request.message, session_state.session_id)
        if self._requests_debugger_model_used(request.message):
            return self._debugger_model_used_response(request.message, session_state.session_id)
        if self._requests_debugger_rag_used(request.message):
            return self._debugger_rag_used_response(request.message, session_state.session_id)
        if self._requests_debugger_hallucination_eval(request.message):
            return self._debugger_hallucination_eval_response(session_state.session_id)
        if self._requests_multimodal_model_as_chat(request.message):
            return self._multimodal_model_chat_block_response(session_state.session_id)
        if self._requests_vision_ocr_status(request.message):
            return self._vision_ocr_status_response(session_state.session_id)
        if self._requests_auto_memory_from_image(request.message):
            return self._image_memory_block_response(session_state.session_id)
        if self._requests_vision_rag_auto_ingest(request.message):
            return self._vision_rag_auto_ingest_block_response(session_state.session_id)
        if self._requests_vision_rag_ingest(request.message):
            return self._vision_rag_ingest_preview_response(session_state.session_id)
        if self._requests_visual_or_ocr_analysis(request.message):
            return self._visual_or_ocr_analysis_guidance_response(request.message, session_state.session_id)
        if self._requests_embedding_or_reranker_as_chat(request.message):
            return self._embedding_reranker_chat_block_response(session_state.session_id)
        if self._requests_model_execution(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="preview",
                message=(
                    "O runtime local esta habilitado para inferencia real governada. "
                    "O chat nao troca nem força um GGUF arbitrario por texto livre; ele usa o binding de role/modelo aprovado pela policy. "
                    "Para escolher um modelo especifico, use preview/execucao rastreavel por role ou uma task com contrato claro."
                ),
                next_actions=[
                    ChatNextAction(type="view_model_status", label="Ver status dos modelos"),
                    ChatNextAction(type="preview_role_model_run", label="Preview role-model"),
                ],
                warnings=["direct_model_selection_requires_policy", "governed_auto_inference_enabled"],
                model_used=None,
                real_inference=False,
            )
        if self._requests_vector_rag_auto_ingest(request.message):
            return self._vector_rag_auto_ingest_block_response(session_state.session_id)
        if self._requests_vector_rag_status(request.message):
            return self._vector_rag_status_response(session_state.session_id)
        if self._requests_vector_rag_ingest(request.message):
            return self._vector_rag_ingest_preview_response(session_state.session_id)
        if self._requests_vector_rag_query(request.message):
            return self._vector_rag_query_from_chat(request, session_state.session_id)
        if self._requests_legacy_vectorstore(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="blocked",
                message="Vectorstore legado esta bloqueado. O Sprint 25 permite apenas retrieval governado read-only, deterministico, com fonte registrada, escopo e citacoes.",
                warnings=["legacy_vectorstore_blocked", "governed_retrieval_only"],
            )
        if self._requests_ignore_citations(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="blocked",
                message="Nao posso ignorar citacoes ao usar retrieval ou memoria curada. Contexto governado exige fonte, provenance e citation map validos.",
                warnings=["context_citations_required", "citation_bypass_blocked"],
            )
        if self._requests_explicit_retrieval(request.message):
            retrieval_response = self._retrieval_from_chat(request, session_state.session_id)
            if retrieval_response is not None:
                return retrieval_response
        if self._requests_memory_auto_or_rag(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="blocked",
                message="Memoria automatica, RAG, vectorstore e embeddings continuam desativados. Posso listar memoria curada por pedido explicito, mas nao vou injeta-la automaticamente no chat ou no PromptAssembly.",
                next_actions=[ChatNextAction(type="view_curated_memory", label="Listar memorias curadas")],
                warnings=["auto_memory_disabled", "rag_disabled", "vectorstore_disabled", "prompt_memory_auto_injection_disabled"],
            )
        if self._requests_curated_memory_list(request.message):
            return self._curated_memory_list_response(session_state.session_id)
        if self._requests_curated_memory_persist(request.message):
            return self._curated_memory_persist_response(request, session_state.session_id)
        if self._requests_memory_approval(request.message):
            return self._memory_approval_from_chat(request, session_state.session_id)
        if self._requests_memory_candidate_list(request.message):
            return self._memory_candidate_list_response(session_state.session_id)
        if self._requests_memory_candidate(request.message):
            candidate_response = self._memory_candidate_from_chat(request, session_state.session_id)
            if candidate_response is not None:
                return candidate_response
        if self._requests_artifact_write_now(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="preview",
                message="Posso orientar a escrita de um artefato aprovado, mas o chat normal nao grava arquivos. Para salvar, use o fluxo explicito: preview aprovado, approval valido, criar ArtifactWriteRun e executar o endpoint de write. Nenhum arquivo foi gravado por esta resposta.",
                next_actions=[ChatNextAction(type="execute_artifact_write", label="Executar escrita aprovada via endpoint explicito")],
                warnings=["chat_does_not_auto_write_files", "artifact_write_requires_explicit_endpoint"],
            )
        if self._requests_patch_quality(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="preview",
                message="Posso validar estaticamente um PatchPlan ou diff pelo Patch Quality Gate. O chat nao aplica patch, nao escreve arquivos e nao executa testes. Sem quality gate passed, nao existe caminho seguro para revisao futura de apply.",
                next_actions=[
                    ChatNextAction(type="validate_patch_quality", label="Validar PatchPlan/diff pelo quality gate"),
                    ChatNextAction(type="view_patch_quality_status", label="Ver status do Patch Quality Gate"),
                ],
                warnings=["patch_quality_gate_required", "chat_does_not_apply_patch", "static_validation_only"],
            )
        if self._requests_patch_apply_status(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="ok",
                message="Posso consultar um PatchApplyRun quando voce informar o run_id. So considero aplicado se o resultado estiver completed e a post_apply_validation estiver passed.",
                next_actions=[ChatNextAction(type="view_patch_apply_run", label="Ver status do PatchApplyRun")],
                warnings=["patch_apply_success_requires_post_validation"],
            )
        if self._requests_patch_rollback(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="preview",
                message="Rollback de patch exige apply_run_id explicito e deve usar o endpoint /api/v1/patch-apply/runs/{apply_run_id}/rollback. O chat normal nao restaura arquivos escondido.",
                next_actions=[ChatNextAction(type="rollback_patch_apply", label="Executar rollback via endpoint explicito")],
                warnings=["chat_does_not_rollback_patch"],
            )
        if self._requests_patch_apply(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="blocked",
                message="Apply de patch pelo chat esta bloqueado. O fluxo seguro exige PatchPlan, diff preview, Patch Quality Gate passed, approval explicito, operator confirmation, execute endpoint e validacao pos-apply. Nenhum arquivo foi alterado.",
                next_actions=[
                    ChatNextAction(type="create_patch_plan", label="Criar proposta de patch"),
                    ChatNextAction(type="validate_patch_quality", label="Validar pelo Patch Quality Gate"),
                    ChatNextAction(type="request_patch_apply_approval", label="Solicitar approval de patch apply"),
                    ChatNextAction(type="execute_patch_apply", label="Executar PatchApplyRun via endpoint explicito"),
                ],
                warnings=["patch_apply_disabled", "chat_auto_apply_disabled", "patch_quality_gate_required", "explicit_approval_required", "post_apply_validation_required"],
            )
        if self._requests_artifact_preview(request.message) and request.context and request.context.active_workspace:
            artifact_response = self._artifact_preview_from_chat(request, session_state.session_id)
            if artifact_response is not None:
                return artifact_response
        if self._requests_smoke_test_from_chat(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="ok",
                message="Smoke test de llama.cpp e inferencia real sao manuais por endpoint/config. O chat nao executa smoke test, nao altera configuracao e nao inicia processo local.",
                warnings=["manual_smoke_test_required", "chat_does_not_run_smoke_test"],
                model_used="stub.default",
                real_inference=False,
            )
        if self._requests_real_inference_from_chat(request.message):
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="ok",
                message="Inferencia real via llama.cpp esta desabilitada por policy/default. O chat nao altera configuracao, nao inicia processo local e nao substitui o stub automaticamente.",
                warnings=["real_inference_disabled_by_policy", "chat_does_not_enable_llama_cpp"],
                model_used="stub.default",
                real_inference=False,
            )
        try:
            analysis_context = request.context.model_dump() if request.context is not None else {}
            analysis = self.prompt_intelligence.analyze(
                PromptAnalysisRequest(
                    prompt=request.message,
                    session_id=session_state.session_id,
                    context=analysis_context,
                )
            )
            intent_map = self._apply_session_context(analysis.intent_map, session_state)
            policy_request = self.prompt_intelligence.to_policy_request(intent_map)
            policy_decision, _canonical_policy = self.policy_decisions.resolve_policy_request(policy_request)
            preview_model = self.policy_decisions.contract_preview_for_policy_request(policy_request)
            contract_preview = _to_dict(preview_model)
            draft = self.task_draft_service.create_from_analysis(intent_map, policy_decision, session_state=session_state)
            status = self._chat_status(intent_map, policy_decision, request)
            preview = self.task_preview_service.create_preview_from_draft(draft.draft_id) if draft is not None and draft.status != "blocked" else None
            if draft is not None and draft.status == "blocked":
                status = "blocked"
            elif draft is not None and draft.status == "needs_clarification":
                status = "needs_clarification"
            elif draft is not None and status == "ok":
                status = "preview"
            task_run, runtime_status = self._materialize_task_run(preview, intent_map, request)
            if runtime_status is not None:
                status = runtime_status
                contract_preview["runtime"] = {
                    "task_id": task_run.run_id,
                    "status": task_run.status,
                    "approval_id": task_run.approval_id,
                    "auto_run_requested": task_run.auto_run_requested,
                }
            message = self.speaker.compose_response(
                request=request,
                intent_map=intent_map,
                policy_decision=policy_decision,
                contract_preview=contract_preview,
                status=status,
            )
            if task_run is not None and status == "pending_approval":
                message = "A task foi criada e esta aguardando sua aprovacao antes de qualquer efeito colateral."
            elif task_run is not None and status == "ready":
                message = "A task entrou no fluxo governado. Vou acompanhar execucao, validacao e resultado pelo estado confirmado."
            model_used = "stub.default"
            real_inference = False
            model_warnings: list[str] = []
            evaluation_status = None
            evaluation_warnings: list[str] = []
            fallback_used = False
            model_trace_items: list[ChatTraceItem] = []
            if status == "ok" and intent_map.intent_type == "conversation" and request.mode == "normal":
                model_attempt = self._conversation_model_response(request, intent_map, policy_decision)
                if model_attempt is not None:
                    message = str(model_attempt["message"])
                    status = str(model_attempt["status"])
                    model_used = str(model_attempt["model_used"])
                    real_inference = bool(model_attempt["real_inference"])
                    model_warnings = list(model_attempt["model_warnings"])
                    evaluation_status = str(model_attempt.get("evaluation_status") or "") or None
                    evaluation_warnings = list(model_attempt.get("evaluation_warnings", []))
                    fallback_used = bool(model_attempt.get("fallback_used", False))
                    model_trace_items = list(model_attempt.get("trace", []))
            message, truncation_warnings = AntiTruncationService(self.response_policy.max_message_chars()).apply(message)
            task_draft_id = draft.draft_id if draft is not None and draft.status != "blocked" else None
            preview_id = preview.preview_id if preview is not None else None
            updated_session = self.session_service.update_after_chat(
                session_state,
                request,
                intent_map,
                policy_decision,
                task_draft_id=task_draft_id,
                status=status,
            )
            if draft is not None:
                self.session_service.append_event(
                    updated_session.session_id,
                    "task_draft_created",
                    f"Task draft registrado com status {draft.status}.",
                    data={
                        "draft_id": draft.draft_id,
                        "draft_status": draft.status,
                        "preview_id": preview_id,
                        "task_id": task_run.run_id if task_run is not None else None,
                        "approval_id": task_run.approval_id if task_run is not None else None,
                    },
                )
            warnings = [*analysis.warnings, *policy_decision.warnings, *truncation_warnings]
            if draft is not None:
                warnings = [*warnings, *draft.warnings]
            if request.use_model_stub:
                stub_result = self._apply_optional_model_stub(request, intent_map, policy_decision, message)
                message = str(stub_result["message"])
                message, stub_truncation_warnings = AntiTruncationService(self.response_policy.max_message_chars()).apply(message)
                model_used = stub_result["model_used"]
                real_inference = bool(stub_result["real_inference"])
                model_warnings = list(stub_result["model_warnings"])
                evaluation_status = str(stub_result.get("evaluation_status") or "") or None
                evaluation_warnings = list(stub_result.get("evaluation_warnings", []))
                fallback_used = bool(stub_result.get("fallback_used", False))
                warnings = [*warnings, *model_warnings, *evaluation_warnings, *stub_truncation_warnings]
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=updated_session.session_id,
                task_draft_id=task_draft_id,
                preview_id=preview_id,
                task_id=task_run.run_id if task_run is not None else None,
                approval_id=task_run.approval_id if task_run is not None else None,
                task_preview_id=preview_id,
                status=status,  # type: ignore[arg-type]
                message=message,
                intent=self._intent_summary(intent_map, detailed=self._include_trace(request)),
                policy=self._policy_summary(policy_decision),
                contract_preview=contract_preview if status in {"preview", "blocked", "needs_clarification", "pending_approval", "ready"} or request.mode in {"preview", "debug"} else {},
                actions=self._suggested_actions(status, policy_decision),
                next_actions=self._runtime_next_actions(task_run) if task_run is not None else self._next_actions(status, draft, preview),
                warnings=list(dict.fromkeys(warnings)),
                trace=[*self._trace_items(analysis.trace, policy_decision, include=self._include_trace(request)), *model_trace_items] if self._include_trace(request) else [],
                raw_debug_ref=None,
                operation_id=operation_decision.operation_id if operation_decision.operation_type != "simple_conversation" else None,
                operation_type=operation_decision.operation_type if operation_decision.operation_type != "simple_conversation" else None,
                message_type=(
                    "clarification_request"
                    if status == "needs_clarification"
                    else "task_preview"
                    if draft is not None and status in {"preview", "pending_approval"}
                    else "task_status_update"
                    if task_run is not None and status == "ready"
                    else "assistant_final_answer"
                ),
                is_final_answer=not (draft is not None and status in {"preview", "needs_clarification", "pending_approval"}),
                grounding_required=bool(draft is not None),
                grounding_missing_reason="task_preview_not_execution_result" if draft is not None and status in {"preview", "needs_clarification", "pending_approval"} else None,
                model_used=model_used,
                real_inference=real_inference,
                model_warnings=model_warnings,
                evaluation_status=evaluation_status,
                evaluation_warnings=evaluation_warnings,
                fallback_used=fallback_used,
            )
        except Exception as exc:
            trace = []
            if self._include_trace(request):
                trace = [ChatTraceItem(stage="chat_service", status="degraded", reason=str(exc), source="services/chat/chat_service.py")]
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_state.session_id,
                status="degraded",
                message="Chat em modo degradado: uma dependencia de analise, policy, sessao ou draft falhou. Nenhuma acao foi executada.",
                warnings=["dependency_unavailable", str(exc)],
                trace=trace,
            )

    def _apply_optional_model_stub(
        self,
        request: ChatRequest,
        intent_map: Any,
        policy_decision: PolicyDecision,
        fallback_message: str,
    ) -> dict[str, object]:
        preview = self.prompt_assembly_service.preview(
            PromptAssemblyRequest(
                purpose="chat",
                role_id="speaker",
                user_message=request.message,
                intent_map=_to_dict(intent_map),
                policy_decision=_to_dict(policy_decision),
                output_contract_type="chat_response",
                model_id=request.model_id or "stub.default",
                include_trace=self._include_trace(request),
            )
        )
        response = self.model_invocation_service.invoke(preview.model_request)
        evaluation = response.evaluation_result or {}
        fallback = evaluation.get("fallback_decision", {}) if isinstance(evaluation, dict) else {}
        fallback_used = bool(fallback.get("should_fallback")) if isinstance(fallback, dict) else False
        if fallback_used and fallback.get("safe_message"):
            message = str(fallback.get("safe_message"))
        else:
            message = response.content.strip() or fallback_message
        return {
            "message": message,
            "model_used": response.model_id,
            "real_inference": response.real_inference,
            "model_warnings": list(dict.fromkeys([*preview.assembly.warnings, *response.warnings])),
            "evaluation_status": evaluation.get("status") if isinstance(evaluation, dict) else None,
            "evaluation_warnings": list(evaluation.get("warnings", [])) if isinstance(evaluation, dict) else [],
            "fallback_used": fallback_used,
        }

    def _conversation_model_response(self, request: ChatRequest, intent_map: Any, policy_decision: PolicyDecision) -> dict[str, object] | None:
        normal_chat = self.chat_model_policy.normal_chat
        output_contract_type = str(normal_chat.get("output_contract_type") or "chat_response")
        configured_model_id = self.chat_model_policy.normal_chat_model_id()
        selected_model_id = request.model_id or configured_model_id
        if not selected_model_id:
            return {
                "status": "degraded",
                "message": "Nao ha modelo configurado para conversa normal.",
                "model_used": None,
                "real_inference": False,
                "model_warnings": ["normal_chat_model_not_configured"],
                "evaluation_status": None,
                "evaluation_warnings": [],
                "fallback_used": True,
                "trace": [
                    ChatTraceItem(
                        stage="conversation_model_selection",
                        status="blocked",
                        reason="normal_chat_model_not_configured",
                        source="services/chat/chat_service.py",
                        data={"role_id": "speaker", "candidate_source": "chat_model_policy"},
                    )
                ],
            }
        preview = self.prompt_assembly_service.preview(
            PromptAssemblyRequest(
                purpose="chat",
                role_id="speaker",
                user_message=request.message,
                intent_map=self._conversation_prompt_intent(intent_map),
                policy_decision=self._conversation_prompt_policy(policy_decision),
                output_contract_type=output_contract_type,
                model_id=selected_model_id,
                include_trace=self._include_trace(request),
            )
        )
        preview.model_request.metadata.update(
            {
                "allow_real_inference": True,
                "manual_mode": False,
                "operator_confirmed": False,
                "auto_conversation_inference": True,
                "include_evaluation_trace": self._include_trace(request),
            }
        )
        self._apply_normal_chat_runtime_limits(preview.model_request)
        response = self.model_invocation_service.invoke(preview.model_request)
        evaluation = response.evaluation_result or {}
        warnings = list(dict.fromkeys([*preview.assembly.warnings, *response.warnings]))
        evaluation_warnings = list(evaluation.get("warnings", [])) if isinstance(evaluation, dict) else []
        fallback_used = not bool(response.real_inference and response.status == "completed")
        trace = [
            ChatTraceItem(
                stage="conversation_model_selection",
                status=response.status,
                reason=response.finish_reason,
                source="services/chat/chat_service.py",
                data={
                    "role_id": "speaker",
                    "requested_capability": "conversation",
                    "purpose": "chat",
                    "candidate_source": "role_model_bindings",
                    "selected_model": response.model_id,
                    "provider": response.provider_id,
                    "fallback_used": fallback_used,
                    "stub_used": response.model_id == "stub.default",
                    "real_inference": response.real_inference,
                    "evaluation_status": evaluation.get("status") if isinstance(evaluation, dict) else None,
                    "latency_ms": response.metadata.get("latency_ms") if isinstance(response.metadata, dict) else None,
                },
            )
        ]
        if response.status == "completed" and response.real_inference and response.content.strip():
            return {
                "status": "ok",
                "message": response.content.strip(),
                "model_used": response.model_id,
                "real_inference": True,
                "model_warnings": warnings,
                "evaluation_status": evaluation.get("status") if isinstance(evaluation, dict) else None,
                "evaluation_warnings": evaluation_warnings,
                "fallback_used": False,
                "trace": trace,
            }
        failure_codes = self._conversation_model_failure_codes(response, warnings)
        reason = ", ".join(failure_codes or warnings) or response.finish_reason or response.status
        return {
            "status": "degraded",
            "message": (
                "Nao consegui gerar uma resposta conversacional pelo modelo leve agora. "
                "O Intent Map classificou como conversa simples; a falha ocorreu na fronteira do modelo speaker/runtime, "
                f"nao na classificacao de intent. reason_code={reason}."
            ),
            "model_used": response.model_id,
            "real_inference": bool(response.real_inference),
            "model_warnings": list(dict.fromkeys([*warnings, *failure_codes, "conversation_model_unavailable"])),
            "evaluation_status": evaluation.get("status") if isinstance(evaluation, dict) else None,
            "evaluation_warnings": evaluation_warnings,
            "fallback_used": True,
            "trace": trace,
        }

    def _conversation_model_failure_codes(self, response: Any, warnings: list[str]) -> list[str]:
        warning_text = " ".join(str(item or "") for item in warnings).casefold()
        codes: list[str] = []
        if str(getattr(response, "finish_reason", "") or "").casefold() == "timeout" or "timeout" in warning_text:
            codes.append("MODEL_TIMEOUT")
        if "stderr" in warning_text or "std_err" in warning_text:
            codes.append("STDERR_CAPTURED")
        if not str(getattr(response, "content", "") or "").strip():
            codes.append("EMPTY_OUTPUT")
        if not bool(getattr(response, "real_inference", False)) or str(getattr(response, "status", "") or "") != "completed":
            codes.append("CONVERSATION_MODEL_UNAVAILABLE")
        return list(dict.fromkeys(codes))

    def _apply_normal_chat_runtime_limits(self, model_request: Any) -> None:
        normal_chat = self.chat_model_policy.normal_chat
        max_output_tokens = int(normal_chat.get("max_output_tokens") or model_request.generation_config.max_tokens)
        model_request.generation_config.max_tokens = max(1, max_output_tokens)
        if "temperature" in normal_chat:
            model_request.generation_config.temperature = float(normal_chat.get("temperature"))
        if "top_p" in normal_chat:
            model_request.generation_config.top_p = float(normal_chat.get("top_p"))
        if "ctx_size" in normal_chat:
            model_request.metadata["ctx_size"] = max(1, int(normal_chat.get("ctx_size") or 1))
        if "timeout_seconds" in normal_chat:
            model_request.metadata["timeout_seconds"] = max(1, int(normal_chat.get("timeout_seconds") or 1))

    def _conversation_prompt_intent(self, intent_map: Any) -> dict[str, Any]:
        value = _to_dict(intent_map)
        return {
            "intent_type": value.get("intent_type"),
            "task_type": value.get("task_type"),
            "requires_task": value.get("requires_task", False),
            "requires_workspace": value.get("requires_workspace", False),
            "requires_approval": value.get("requires_approval", False),
            "output_channel": value.get("output_channel", "chat"),
        }

    def _conversation_prompt_policy(self, policy_decision: PolicyDecision) -> dict[str, Any]:
        value = _to_dict(policy_decision)
        return {
            "safe_to_execute": value.get("safe_to_execute"),
            "allowed_actions": value.get("allowed_actions", []),
            "approval_required_for": value.get("approval_required_for", []),
            "blocked_reasons": value.get("blocked_reasons", []),
        }

    def _readonly_project_analysis_preview_response(
        self,
        session_id: str,
        decision,
        *,
        workspace_ref: str | None,
    ) -> ChatResponse:
        public_operation_type = str(decision.metadata.get("router_operation_type") or decision.operation_type)
        if not workspace_ref:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="needs_clarification",
                message=(
                    "Preciso saber qual workspace ou projeto devo analisar em modo somente leitura. "
                    "Escolha um workspace legivel ou informe um caminho registrado."
                ),
                intent={"intent_type": "readonly_project_analysis", "requires_task": True, "requires_workspace": True},
                policy={"approval_required_for": [], "read_only": True},
                operation_id=decision.operation_id,
                operation_type=public_operation_type,
                message_type="clarification_request",
                requires_user_action=True,
                is_final_answer=False,
                grounded=False,
                grounding_required=True,
                grounding_missing_reason="workspace_missing",
                warnings=["workspace_required_but_missing"],
            )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="preview",
            message=(
                f"Posso iniciar uma analise somente leitura de {workspace_ref}. "
                "Ainda nao li arquivos nem gerei conclusao sobre o projeto; isto e uma previa operacional. "
                "Nenhuma escrita sera feita nesse workspace por esta resposta."
            ),
            intent={"intent_type": "readonly_project_analysis", "requires_task": True, "requires_workspace": True},
            policy={"approval_required_for": [], "read_only": True, "workspace_id": workspace_ref},
            operation_id=decision.operation_id,
            operation_type=public_operation_type,
            message_type="task_preview",
            requires_user_action=True,
            is_final_answer=False,
            grounded=False,
            grounding_required=True,
            grounding_missing_reason="read_files_not_executed",
            warnings=["readonly_preview_not_project_summary"],
        )

    def _requests_task_status(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"status da task", "como esta a task", "como está a task", "estado da task", "resultado da task"})

    def _requests_smoke_test_from_chat(self, message: str) -> bool:
        lowered = message.lower()
        return "smoke" in lowered and ("llama" in lowered or "modelo" in lowered or "inferencia" in lowered or "inferÃªncia" in lowered)

    def _requests_real_inference_from_chat(self, message: str) -> bool:
        lowered = message.lower()
        real_terms = {"modelo real", "inferencia real", "inferÃªncia real", "llama real", "llama.cpp"}
        activation_terms = {"use", "usar", "ative", "ativar", "habilite", "habilitar"}
        return any(term in lowered for term in real_terms) and any(term in lowered for term in activation_terms)

    def _requests_debugger_mutation(self, message: str) -> bool:
        lowered = message.lower()
        return "debugger" in lowered and any(term in lowered for term in {"aplique", "aplicar", "corrija", "execute", "executar", "rode", "rodar", "mutar", "alterar arquivo"})

    def _requests_raw_debug_prompt(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"raw prompt", "prompt bruto", "raw output", "saida bruta", "saída bruta", "raw log"})

    def _requests_debugger_blocked_reason(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"por que foi bloqueado", "porque foi bloqueado", "why blocked", "motivo do bloqueio", "blocked reason"})

    def _requests_debugger_model_used(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"qual modelo foi usado", "modelo usado", "model used", "por que escolheu modelo", "modelo escolhido"})

    def _requests_debugger_rag_used(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"rag foi usado", "usou rag", "qual rag", "namespace usado", "chunks recuperados"})

    def _requests_debugger_hallucination_eval(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"teve hallucination", "teve alucinacao", "teve alucinação", "citation coverage", "grounding", "avaliar grounding"})

    def _debugger_read_only_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message="Debugger 2.0 e Evaluation Workbench sao read-only. Eles explicam traces, choices, findings e riscos, mas nao aplicam patch, nao escrevem workspace, nao executam shell/git, nao aprovam memoria e nao executam ingestao RAG.",
            next_actions=[ChatNextAction(type="view_debugger_status", label="Ver status do Debugger 2.0")],
            warnings=["debugger_read_only", "mutation_from_debugger_blocked"],
        )

    def _raw_debug_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message="Raw prompt/output/log fica oculto por padrao. O Debugger mostra timeline sanitizada, source refs, warnings e blocked_reasons. Secrets continuam redigidos mesmo em modo interno.",
            next_actions=[ChatNextAction(type="view_debugger_timeline", label="Ver timeline sanitizada")],
            warnings=["raw_prompt_hidden_by_default", "raw_output_hidden_by_default", "secrets_redacted"],
        )

    def _debugger_blocked_reason_response(self, message: str, session_id: str | None) -> ChatResponse:
        target = self._extract_debug_target_id(message)
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if target else "needs_clarification",
            message="Posso explicar o bloqueio usando Debugger 2.0: timeline sanitizada, blocked_reasons, policy/gate e source refs. Informe um trace_id/run_id se quiser resolver um alvo especifico." if not target else f"Use /api/v1/debugger/traces/resolve e a timeline sanitizada para {target}; o Debugger nao muta nada.",
            next_actions=[ChatNextAction(type="resolve_debugger_trace", label="Resolver trace/run", target_id=target), ChatNextAction(type="view_debugger_timeline", label="Ver timeline", target_id=target)],
            warnings=["debugger_read_only", "sanitized_trace_only"],
        )

    def _debugger_model_used_response(self, message: str, session_id: str | None) -> ChatResponse:
        target = self._extract_debug_target_id(message)
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if target else "needs_clarification",
            message="A escolha de modelo precisa ser auditavel: model_id, role_id, provider, fallback, doctor status, manual escalation e evaluation. Informe um run_id para inspecionar." if not target else f"Inspecione {target} em /api/v1/debugger/model-runs/{target} ou /api/v1/debugger/role-runs/{target}.",
            next_actions=[ChatNextAction(type="inspect_model_run", label="Inspecionar modelo", target_id=target), ChatNextAction(type="inspect_role_run", label="Inspecionar role", target_id=target)],
            warnings=["model_choice_requires_audit_trace"],
        )

    def _debugger_rag_used_response(self, message: str, session_id: str | None) -> ChatResponse:
        target = self._extract_debug_target_id(message)
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if target else "needs_clarification",
            message="Uso de RAG precisa mostrar namespace, query_id, chunks, scores, reranker, citations e ContextAdmission. Informe query_id para inspecionar." if not target else f"Inspecione {target} em /api/v1/debugger/rag-runs/{target}.",
            next_actions=[ChatNextAction(type="inspect_rag_run", label="Inspecionar RAG", target_id=target)],
            warnings=["rag_usage_requires_citations_and_trace"],
        )

    def _debugger_hallucination_eval_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message="Posso avaliar sinais de hallucination de forma read-only: citações fabricadas, claims de patch/test/memoria/RAG sem resultado, Vision/OCR sem trace e referências fora do contexto.",
            next_actions=[ChatNextAction(type="run_hallucination_eval", label="Usar /api/v1/evals/hallucination-signals"), ChatNextAction(type="run_grounding_eval", label="Usar /api/v1/evals/context-grounding")],
            warnings=["evals_read_only", "no_auto_fix"],
        )

    def _extract_debug_target_id(self, message: str) -> str | None:
        import re
        match = re.search(r"\b(trace|role_model_run|rag_query|context_plan|vision_run|ocr_run|patch_apply_run|eval_run|validation)_[A-Za-z0-9_]+", message)
        return match.group(0) if match else None
    def _requests_multimodal_model_as_chat(self, message: str) -> bool:
        lowered = message.lower()
        model_terms = {"qwen2.5-vl", "qwen2_5_vl", "qwen vl", "llava", "nanonets", "ocr model", "modelo ocr", "vision model", "modelo vision", "modelo visual"}
        chat_terms = {"chat", "conversa", "speaker", "responda", "responder", "use como chat", "usar como chat", "rode no chat"}
        catalog_terms = {"status", "listar", "liste", "quais", "catalogo", "catálogo", "registrado", "registrados"}
        return any(term in lowered for term in model_terms) and any(term in lowered for term in chat_terms) and not any(term in lowered for term in catalog_terms)

    def _requests_vision_ocr_status(self, message: str) -> bool:
        lowered = message.lower()
        area_terms = {"vision", "visao", "visão", "ocr", "multimodal", "imagem", "image", "llava", "nanonets", "qwen2.5-vl", "qwen2_5_vl"}
        status_terms = {"status", "health", "doctor", "configurado", "configurados", "ligado", "ligados", "listar", "liste", "quais"}
        return any(term in lowered for term in area_terms) and any(term in lowered for term in status_terms)

    def _requests_visual_or_ocr_analysis(self, message: str) -> bool:
        lowered = message.lower()
        object_terms = {"imagem", "image", "screenshot", "print", "foto", "diagrama", "diagram", "documento visual", "pdf", "ocr"}
        action_terms = {"analise", "analisar", "descreva", "descrever", "interprete", "interpretar", "leia", "ler", "extraia", "extrair", "transcreva", "transcrever"}
        return self._contains_bounded_term(lowered, object_terms) and self._contains_bounded_term(lowered, action_terms)

    def _contains_bounded_term(self, text: str, terms: set[str]) -> bool:
        import re

        return any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", text)
            for term in terms
        )

    def _requests_auto_memory_from_image(self, message: str) -> bool:
        lowered = message.lower()
        image_terms = {"imagem", "image", "screenshot", "foto", "ocr", "documento visual"}
        memory_terms = {"memoria", "memória", "guarde", "guardar", "aprenda", "salve", "salvar", "registre"}
        return any(term in lowered for term in image_terms) and any(term in lowered for term in memory_terms)

    def _requests_vision_rag_ingest(self, message: str) -> bool:
        lowered = message.lower()
        ingest_terms = {"ingest", "ingestao", "ingestão", "indexe", "indexar", "crie indice", "crie índice", "criar indice", "criar índice"}
        visual_terms = {"vision-rag", "vision rag", "ocr-rag", "ocr rag", "imagem", "image", "ocr", "visual"}
        return any(term in lowered for term in ingest_terms) and any(term in lowered for term in visual_terms)

    def _requests_vision_rag_auto_ingest(self, message: str) -> bool:
        lowered = message.lower()
        auto_terms = {"automatico", "automático", "auto", "sem approval", "sem aprovacao", "sem aprovação", "direto", "imediato"}
        return self._requests_vision_rag_ingest(message) and any(term in lowered for term in auto_terms)

    def _message_has_visual_source_reference(self, message: str) -> bool:
        import re
        return bool(re.search(r"(?i)([A-Z]:[\\/][^\n\r\"']+\.(png|jpe?g|webp|bmp|tiff?|pdf)|[^\s\"']+\.(png|jpe?g|webp|bmp|tiff?|pdf))", message))

    def _multimodal_model_chat_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message="Modelos Vision/OCR nao sao usados como chat comum. Eles so podem entrar pelo pipeline governado de Vision/OCR, com source_ref, citacao, confidence, trace e avaliacao. Nenhuma imagem foi enviada ao prompt diretamente.",
            next_actions=[ChatNextAction(type="view_vision_status", label="Ver status Vision/OCR")],
            warnings=["multimodal_model_not_chat_model", "vision_pipeline_required", "raw_image_not_prompt_context"],
            model_used="stub.default",
            real_inference=False,
        )

    def _vision_ocr_status_response(self, session_id: str | None) -> ChatResponse:
        from aipinho.services.vision.vision_status_service import VisionStatusService

        status = VisionStatusService().status()
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if status.get("status") == "ok" else "degraded",
            message=(
                f"Vision/OCR governado: vision_runtime={status.get('vision_runtime_enabled')}, "
                f"ocr_runtime={status.get('ocr_runtime_enabled')}, vision_rag={status.get('vision_rag_enabled')}, "
                f"ocr_rag={status.get('ocr_rag_enabled')}. Raw de imagem e OCR nao entram no chat nem na memoria automaticamente."
            ),
            next_actions=[ChatNextAction(type="view_vision_status", label="Ver /api/v1/vision/status")],
            warnings=list(dict.fromkeys([*list(status.get("warnings", [])), *list(status.get("blocked_reasons", [])), "raw_image_context_disabled", "auto_vision_rag_disabled"])),
        )

    def _image_memory_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message="Nao salvo imagem, OCR ou resultado visual como memoria definitiva automaticamente. Primeiro o conteudo precisa virar evidencia citada, depois candidato curado, com fonte, escopo, dedupe, conflito resolvido e approval explicito.",
            next_actions=[ChatNextAction(type="create_memory_candidate", label="Criar candidato curado apos evidencia")],
            warnings=["raw_image_memory_blocked", "ocr_memory_requires_curation", "explicit_memory_approval_required"],
        )

    def _vision_rag_auto_ingest_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message="Vision RAG/OCR RAG nao ingere imagem, blob ou OCR automaticamente. O fluxo seguro exige resultado visual/OCR com citacao e confidence, preview de ingestao, approval e execucao explicita.",
            next_actions=[ChatNextAction(type="create_vision_rag_ingestion_preview", label="Criar preview governado")],
            warnings=["vision_rag_auto_ingest_blocked", "raw_image_vector_ingestion_blocked", "approval_required"],
        )

    def _vision_rag_ingest_preview_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message="Posso orientar um preview de ingestao Vision RAG/OCR RAG, mas nao indexo imagem bruta nem OCR sem evidencia. Use /api/v1/vision-rag/ingest-preview com um VisionAnalysisResult ou OCRResult citado.",
            next_actions=[
                ChatNextAction(type="create_vision_rag_ingestion_preview", label="Criar preview Vision/OCR RAG"),
                ChatNextAction(type="request_vision_rag_ingestion_approval", label="Solicitar approval de ingestao"),
            ],
            warnings=["chat_does_not_ingest_vision_rag", "preview_required", "approval_required", "visual_citations_required"],
        )

    def _visual_or_ocr_analysis_guidance_response(self, message: str, session_id: str | None) -> ChatResponse:
        has_source = self._message_has_visual_source_reference(message)
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview" if has_source else "needs_clarification",
            message=(
                "Posso analisar imagem/OCR somente pelo pipeline governado. "
                "Forneca um ImageInput com source_ref explicito; a saida precisa ter fonte, regiao/pagina quando possivel, confidence, citacao, trace e avaliacao. "
                "O chat nao coloca imagem nem OCR bruto no contexto."
            ),
            next_actions=[
                ChatNextAction(type="run_vision_analysis", label="Usar /api/v1/vision/analyze"),
                ChatNextAction(type="run_ocr_extract", label="Usar /api/v1/ocr/extract"),
                ChatNextAction(type="view_vision_status", label="Ver status Vision/OCR"),
            ],
            warnings=["source_ref_required" if not has_source else "explicit_vision_endpoint_required", "raw_image_not_prompt_context", "ocr_not_truth_without_evaluation"],
        )
    def _requests_model_catalog(self, message: str) -> bool:
        lowered = message.lower()
        model_terms = {"modelo", "modelos", "gguf", "llm", "qwen", "deepseek", "starcoder", "llava", "nanonets"}
        catalog_terms = {"quais", "listar", "liste", "disponiveis", "disponíveis", "registrados", "status", "health"}
        return any(term in lowered for term in model_terms) and any(term in lowered for term in catalog_terms)

    def _requests_model_execution(self, message: str) -> bool:
        lowered = message.lower()
        model_terms = {"modelo", "modelos", "gguf", "llm", "qwen", "deepseek", "starcoder", "llava", "nanonets", "14b", "7b"}
        execution_terms = {"use", "usar", "rode", "rodar", "execute", "executar", "carregue", "carregar", "inferencia", "inferência", "ative", "ativar", "habilite"}
        return any(term in lowered for term in model_terms) and any(term in lowered for term in execution_terms)

    def _model_catalog_response(self, session_id: str | None) -> ChatResponse:
        status = ModelStatusService().status()
        role_status = RoleModelStatusService().status()
        registry = status.get("registry", {}) if isinstance(status.get("registry", {}), dict) else {}
        model_ids = registry.get("runtime_model_ids", []) if isinstance(registry.get("runtime_model_ids", []), list) else []
        default_candidate = registry.get("default_coding_candidate")
        role_default = role_status.get("default_coding_model", "qwen2_5_coder_7b_q4_k_m")
        listed = ", ".join(str(item) for item in model_ids[:14])
        message = (
            f"Ha {registry.get('registered_local_models', len(model_ids))} modelos locais registrados para status/doctor. "
            f"Candidato futuro para codigo: {default_candidate or 'nao definido'}. "
            f"Default controlado por role para codigo: {role_default}. "
            f"Modelos: {listed}. "
            "Conversas e tasks podem usar inferencia real governada quando a policy permitir; este catalogo e uma resposta de status e nao precisou invocar modelo."
        )
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok",
            message=message,
            next_actions=[ChatNextAction(type="view_model_status", label="Ver status dos modelos")],
            warnings=["model_catalog_status_only", "governed_auto_inference_enabled"],
            model_used=None,
            real_inference=False,
        )

    def _requests_embedding_or_reranker_as_chat(self, message: str) -> bool:
        lowered = message.lower()
        model_terms = {
            "qwen3_embedding",
            "qwen3-reranker",
            "qwen3_reranker",
            "embedding model",
            "modelo de embedding",
            "reranker model",
            "modelo reranker",
        }
        chat_terms = {"chat", "converse", "conversar", "responda", "responder", "gerar resposta", "use como modelo"}
        return any(term in lowered for term in model_terms) and any(term in lowered for term in chat_terms)

    def _embedding_reranker_chat_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message=(
                "Modelos de embedding e reranker sao exclusivos do Vector RAG governado. "
                "Eles nao podem ser usados como chat, planner, executor ou ferramenta generativa."
            ),
            next_actions=[ChatNextAction(type="view_vector_rag_status", label="Ver status do Vector RAG")],
            warnings=["embedding_not_chat_model", "reranker_not_chat_model", "vector_rag_model_boundary_enforced"],
            model_used="stub.default",
            real_inference=False,
        )

    def _requests_vector_rag_status(self, message: str) -> bool:
        lowered = message.lower()
        vector_terms = {"vector rag", "vector-rag", "rag vetorial", "namespace", "namespaces", "embedding", "rerank", "reranker"}
        status_terms = {"status", "health", "doctor", "configurado", "configurados", "ligado", "ligados", "listar", "liste", "quais"}
        return ("rag" in lowered or "vector" in lowered) and any(term in lowered for term in vector_terms) and any(term in lowered for term in status_terms)

    def _requests_vector_rag_query(self, message: str) -> bool:
        lowered = message.lower()
        if self._requests_vector_rag_ingest(message) or self._requests_memory_auto_or_rag(message):
            return False
        query_terms = {"busque", "buscar", "procure", "pesquise", "consulta", "query", "recupere", "retrieve", "retrieval"}
        vector_terms = {"vector rag", "vector-rag", "rag vetorial", "namespace", "global", "coder", "reviewer", "debugger", "planner"}
        return "rag" in lowered and any(term in lowered for term in query_terms) and any(term in lowered for term in vector_terms)

    def _requests_vector_rag_ingest(self, message: str) -> bool:
        lowered = message.lower()
        ingest_terms = {"ingest", "ingestao", "ingestão", "indexe", "indexar", "crie indice", "crie índice", "criar indice", "criar índice"}
        vector_terms = {"rag", "vector", "vetorial", "namespace", "embedding"}
        return any(term in lowered for term in ingest_terms) and any(term in lowered for term in vector_terms)

    def _requests_vector_rag_auto_ingest(self, message: str) -> bool:
        lowered = message.lower()
        auto_terms = {"automatico", "automático", "auto", "sem approval", "sem aprovacao", "sem aprovação", "direto", "imediato"}
        return self._requests_vector_rag_ingest(message) and any(term in lowered for term in auto_terms)

    def _vector_rag_status_response(self, session_id: str | None) -> ChatResponse:
        status = VectorRAGStatusService().status()
        namespaces = status.namespaces if hasattr(status, "namespaces") else []
        enabled = [str(item.get("namespace_id")) for item in namespaces if isinstance(item, dict) and item.get("enabled")]
        message = (
            f"Vector RAG governado: {status.mode}. "
            f"Embedding: {status.embedding_model} ({'enabled' if status.embedding_runtime_enabled else 'disabled'}). "
            f"Reranker: {status.reranker_model} ({'enabled' if status.reranker_runtime_enabled else 'disabled'}). "
            f"Namespaces ativos: {', '.join(enabled) or 'nenhum'}. "
            "Legacy vectorstore e auto-ingest permanecem bloqueados."
        )
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if not status.blocked_reasons else "degraded",
            message=message,
            next_actions=[
                ChatNextAction(type="view_vector_rag_status", label="Ver status Vector RAG"),
                ChatNextAction(type="view_vector_rag_namespaces", label="Ver namespaces"),
            ],
            warnings=list(dict.fromkeys([*status.warnings, *status.blocked_reasons, "legacy_vectorstore_disabled", "auto_ingest_disabled"])),
        )

    def _vector_rag_ingest_preview_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message=(
                "Ingestao Vector RAG nao acontece pelo corpo do chat. O fluxo seguro e: "
                "POST /api/v1/vector-rag/ingest-preview, depois approval explicito, depois "
                "POST /api/v1/vector-rag/ingest-execute. Sem fonte, citacao, escopo e approval, nada entra no indice."
            ),
            next_actions=[
                ChatNextAction(type="create_vector_rag_ingestion_preview", label="Criar preview de ingestao"),
                ChatNextAction(type="request_vector_rag_ingestion_approval", label="Solicitar approval de ingestao"),
            ],
            warnings=["chat_does_not_ingest_vector_rag", "preview_required", "approval_required", "citations_required"],
        )

    def _vector_rag_auto_ingest_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message="Auto-ingestao de Vector RAG esta bloqueada. Todo chunk precisa de fonte permitida, escopo, citacao, preview e approval antes de qualquer escrita no indice governado.",
            next_actions=[ChatNextAction(type="create_vector_rag_ingestion_preview", label="Criar preview governado")],
            warnings=["vector_rag_auto_ingest_blocked", "approval_required", "source_citation_scope_required"],
        )

    def _vector_rag_query_from_chat(self, request: ChatRequest, session_id: str | None) -> ChatResponse:
        from aipinho.schemas.rag.vector.contracts import RAGQueryRequest
        from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService

        role_id = self._extract_vector_rag_role(request.message)
        namespace_id = self._extract_vector_rag_namespace(request.message)
        if not role_id and not namespace_id:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Posso consultar o Vector RAG governado, mas preciso de um namespace ou papel claro, como coder, code_reviewer ou global. Nao vou escolher fonte por conta propria.",
                next_actions=[ChatNextAction(type="choose_vector_rag_namespace", label="Escolher namespace/papel")],
                warnings=["vector_rag_scope_required", "model_cannot_select_namespace"],
            )
        result = RAGVectorQueryService().query(
            RAGQueryRequest(
                query=request.message,
                role_id=role_id,
                namespace_id=namespace_id,
                top_k=5,
                include_trace=self._include_trace(request),
            )
        )
        if result.status == "blocked":
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message=f"Vector RAG bloqueado. Motivos: {', '.join(result.blocked_reasons) or 'policy'}. Nenhum contexto foi usado.",
                warnings=list(dict.fromkeys([*result.warnings, *result.blocked_reasons])),
            )
        if not result.hits:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="ok",
                message="Vector RAG consultado, mas nenhum chunk citado foi encontrado. Nao vou responder inventando sem fonte.",
                next_actions=[ChatNextAction(type="view_vector_rag_query", label="Ver query Vector RAG", target_id=result.query_id)],
                warnings=list(dict.fromkeys([*result.warnings, "vector_rag_no_results", "no_answer_without_citation"])),
            )
        citation_summaries = [f"{hit.chunk_id}:{hit.source_ref.ref}" for hit in result.hits[:5]]
        citation_map = {
            citation.citation_id: citation.model_dump()
            for citation in (result.context_bundle.citations if result.context_bundle else [])
        }
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if result.status == "found" else "degraded",
            message=(
                f"Vector RAG encontrou {len(result.hits)} chunk(s) citado(s) em {', '.join(result.namespace_ids)}. "
                f"Citacoes: {', '.join(citation_summaries)}. "
                "O contexto permanece governado; namespace e fonte nao foram escolhidos pelo modelo."
            ),
            next_actions=[ChatNextAction(type="view_vector_rag_query", label="Ver query Vector RAG", target_id=result.query_id)],
            warnings=list(dict.fromkeys([*result.warnings, "explicit_vector_rag_query", "citations_preserved"])),
            context_plan_id=result.context_bundle.bundle_id if result.context_bundle else None,
            citation_map=citation_map,
        )

    def _extract_vector_rag_role(self, message: str) -> str | None:
        from aipinho.services.rag.vector.role_rag_policy_service import RoleRAGPolicyService

        lowered = message.lower()
        for role_id in RoleRAGPolicyService().status().get("roles", []):
            role = str(role_id)
            if role and role.lower() in lowered:
                return role
        return None

    def _extract_vector_rag_namespace(self, message: str) -> str | None:
        from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry

        lowered = message.lower()
        registry = VectorIndexRegistry()
        for namespace in registry.list_namespaces(include_disabled=False):
            if namespace.namespace_id.lower() in lowered:
                return namespace.namespace_id
            if namespace.namespace_type == "global" and "global" in lowered:
                return namespace.namespace_id
        return None

    def _requests_memory_candidate(self, message: str) -> bool:
        lowered = message.lower()
        memory_subject_terms = {
            "memoria",
            "memória",
        }
        memory_action_terms = {
            "lembre",
            "lembrar",
            "guarde",
            "guardar",
            "aprenda",
            "registre",
        }
        return self._contains_bounded_term(lowered, memory_subject_terms) and self._contains_bounded_term(lowered, memory_action_terms)

    def _requests_memory_candidate_list(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"memoria candidata", "memória candidata", "candidatos de memoria", "candidatos de memória"})

    def _requests_memory_approval(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"aprove esse candidato", "aprove esta memoria", "aprove esta memória", "aprovar candidato", "aprovar memória", "aprovar memoria"}) or ("mem" in lowered and "aprov" in lowered)

    def _requests_legacy_vectorstore(self, message: str) -> bool:
        lowered = message.lower()
        return "vectorstore" in lowered and any(term in lowered for term in {"legado", "antigo", "legacy"})

    def _requests_explicit_retrieval(self, message: str) -> bool:
        lowered = message.lower()
        if self._requests_memory_auto_or_rag(message):
            return False
        return any(term in lowered for term in {"busque", "buscar", "procure", "pesquise", "recupere", "retrieval", "use a memória curada", "use a memoria curada", "usando contexto", "contexto do projeto"})

    def _retrieval_from_chat(self, request: ChatRequest, session_id: str | None) -> ChatResponse | None:
        from aipinho.schemas.rag.retrieval_request import RetrievalRequest, RetrievalScope
        from aipinho.schemas.rag.integration.contracts import ContextAdmissionRequest, RAGMemoryPolicyRequest
        from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
        from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
        from aipinho.services.rag.integration.rag_memory_policy_service import RAGMemoryPolicyService
        from aipinho.services.rag.retrieval_service import RetrievalService

        lowered = request.message.lower()
        workspace = request.context.active_workspace if request.context else None
        sources: list[str] = []
        if "memória curada" in lowered or "memoria curada" in lowered:
            sources.append("curated_memory")
        if "relatório" in lowered or "relatorio" in lowered or "relatórios" in lowered or "relatorios" in lowered:
            sources.append("project_reports")
        if "arquivo" in lowered or "contexto do projeto" in lowered:
            sources.append("project_files")
        if not sources:
            sources = ["project_reports"]
        paths = self._extract_retrieval_paths(request.message)
        if "project_files" in sources and not paths:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Posso fazer retrieval governado em arquivos, mas preciso de paths escopados. Sem fonte e escopo claros, nao recupero contexto.",
                next_actions=[ChatNextAction(type="provide_retrieval_scope", label="Informar fonte/path")],
                warnings=["retrieval_scope_required", "file_paths_required"],
            )
        result = RetrievalService().retrieve(
            RetrievalRequest(
                query=request.message,
                sources=sources,
                workspace=workspace,
                paths=paths,
                explicit=True,
                include_trace=self._include_trace(request),
                scope=RetrievalScope(scope_type="workspace" if workspace else "project", workspace=workspace, source_ids=sources),
            )
        )
        if result.status == "blocked":
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message=f"Retrieval governado bloqueado. Motivos: {', '.join(result.blocked_reasons) or 'policy'}. Nenhum contexto foi usado.",
                warnings=list(dict.fromkeys([*result.warnings, *result.blocked_reasons])),
            )
        if not result.hits:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="ok",
                message="Retrieval governado executado, mas nenhum resultado citado foi encontrado. Nao vou inventar resposta sem fonte.",
                next_actions=[ChatNextAction(type="view_retrieval", label="Ver retrieval", target_id=result.retrieval_id)],
                warnings=list(dict.fromkeys([*result.warnings, "retrieval_no_results", "no_answer_without_citation"])),
            )
        policy = RAGMemoryPolicyService().decide(
            RAGMemoryPolicyRequest(
                usage_mode="explicit_user_request",
                intent_type="explicit_retrieval",
                workspace=workspace,
                requested_sources=sources,
                allow_retrieval=any(source != "curated_memory" for source in sources),
                allow_curated_memory="curated_memory" in sources,
                scope={"workspace": workspace, "paths": paths},
                user_request=request.message,
                include_trace=self._include_trace(request),
            )
        )
        if not policy.allowed:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message=f"O uso do contexto foi bloqueado pela policy. Motivos: {', '.join(policy.blocked_reasons) or 'policy'}.",
                warnings=list(dict.fromkeys([*result.warnings, *policy.blocked_reasons])),
            )
        admission = ContextAdmissionService().admit(
            ContextAdmissionRequest(
                policy_decision=policy,
                retrieval_result=result.model_dump(),
                retrieval_context_bundle=result.context_bundle.model_dump() if result.context_bundle else None,
                scope={"workspace": workspace} if workspace else {},
                usage_mode="explicit_user_request",
                include_trace=self._include_trace(request),
            )
        )
        plan = ContextInjectionPlanner().plan(admission, policy_decision_id=policy.decision_id)
        if not plan.safe_for_prompt_assembly:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message=f"O retrieval terminou, mas o contexto nao passou no admission gate. Motivos: {', '.join(plan.blocked_reasons) or 'context policy'}. Nenhum contexto foi usado.",
                next_actions=[ChatNextAction(type="view_retrieval", label="Ver retrieval", target_id=result.retrieval_id)],
                warnings=list(dict.fromkeys([*result.warnings, *plan.warnings, *plan.blocked_reasons])),
                context_plan_id=plan.plan_id,
            )
        citation_summaries = [
            f"{citation_id}:{(citation.get('source_ref') or {}).get('ref')}"
            for citation_id, citation in list(sorted(plan.citation_map.citations.items()))[:5]
        ]
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok" if result.status == "found" else "degraded",
            message=f"Contexto governado admitido com {len(plan.context_items)} item(ns). Fontes: {', '.join(result.sources_used)}. Citacoes usadas: {', '.join(citation_summaries)}. O plano {plan.plan_id} preserva escopo, provenance e budget; nenhuma fonte foi escolhida pelo modelo.",
            next_actions=[
                ChatNextAction(type="view_retrieval", label="Ver retrieval", target_id=result.retrieval_id),
                ChatNextAction(type="view_context_plan", label="Ver plano de contexto", target_id=plan.plan_id),
            ],
            warnings=list(dict.fromkeys([*result.warnings, *plan.warnings, "explicit_governed_context", "no_vectorstore", "no_embeddings"])),
            context_plan_id=plan.plan_id,
            citation_map=plan.citation_map.model_dump(),
        )

    def _requests_ignore_citations(self, message: str) -> bool:
        return not self.context_prompt_policy.evaluate_user_message(message).allowed

    def _extract_retrieval_paths(self, message: str) -> list[str]:
        import re

        matches = re.findall(r"(?i)(?:src|tests|config|docs|reports|scripts)[\\/][^\s\"']+\.[A-Za-z0-9]+", message)
        return [item.strip(".,;") for item in matches]

    def _requests_curated_memory_list(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"memorias curadas", "memórias curadas", "memoria curada", "memória curada"})

    def _requests_curated_memory_persist(self, message: str) -> bool:
        lowered = message.lower()
        return "persist" in lowered and ("memoria" in lowered or "memória" in lowered or "candidato" in lowered)

    def _requests_memory_auto_or_rag(self, message: str) -> bool:
        lowered = message.lower()
        return ("mem" in lowered and any(term in lowered for term in {"automatica", "automática", "auto-injec", "auto injec"})) or ("rag" in lowered and any(term in lowered for term in {"ative", "ativar", "habilite", "usar"}))

    def _memory_approval_from_chat(self, request: ChatRequest, session_id: str | None) -> ChatResponse:
        from aipinho.services.memory.memory_approval_service import MemoryApprovalService

        candidate_id = self._extract_id(request.message, "memcand_")
        if not candidate_id:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Posso criar um approval para persistir memoria curada, mas preciso do candidate_id. Criar approval nao persiste memoria.",
                next_actions=[ChatNextAction(type="view_memory_candidates", label="Ver candidatos de memoria")],
                warnings=["candidate_id_required", "approval_does_not_persist_memory"],
            )
        result = MemoryApprovalService().request_from_candidate(candidate_id, reason="chat_requested_memory_approval")
        if result.status == "blocked":
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message=f"Nao criei approval para {candidate_id}. Motivos: {', '.join(result.blocked_reasons) or 'policy'}. Nenhuma memoria foi persistida.",
                next_actions=[ChatNextAction(type="view_memory_candidate", label="Ver candidato", target_id=candidate_id)],
                warnings=[*result.blocked_reasons, "memory_not_persisted"],
            )
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message=f"Criei approval {result.approval_id} para persistir o candidato {candidate_id} como memoria curada. Ele ainda nao foi persistido. Persistencia exige aprovar o approval e chamar o endpoint explicito de persist.",
            next_actions=[
                ChatNextAction(type="approve_memory_approval", label="Aprovar approval de memoria", target_id=result.approval_id),
                ChatNextAction(type="persist_curated_memory", label="Persistir memoria curada via endpoint explicito", target_id=result.approval_id),
            ],
            warnings=["approval_does_not_persist_memory", "explicit_persist_endpoint_required", "no_auto_prompt_memory"],
        )

    def _curated_memory_persist_response(self, request: ChatRequest, session_id: str | None) -> ChatResponse:
        candidate_id = self._extract_id(request.message, "memcand_")
        approval_id = self._extract_id(request.message, "approval_")
        if not candidate_id or not approval_id:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message="Nao persisti memoria pelo chat. Persistencia exige candidate_id, approval_id aprovado, confirmacao do operador e endpoint explicito /api/v1/memory/approvals/{approval_id}/persist.",
                next_actions=[ChatNextAction(type="request_memory_approval", label="Criar approval de memoria")],
                warnings=["chat_does_not_persist_memory_hidden", "approval_required", "explicit_persist_endpoint_required"],
            )
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message=f"Para persistir o candidato {candidate_id}, aprove o approval {approval_id} e use o endpoint explicito com operator_confirmed=true. O chat nao persiste memoria escondido.",
            next_actions=[ChatNextAction(type="persist_curated_memory", label="Persistir memoria curada via endpoint explicito", target_id=approval_id)],
            warnings=["chat_does_not_persist_memory_hidden", "operator_confirmation_required"],
        )

    def _curated_memory_list_response(self, session_id: str | None) -> ChatResponse:
        from aipinho.services.memory.curated_memory_service import CuratedMemoryService

        memories = CuratedMemoryService().list_memories(status="active", limit=10)
        summary = "; ".join(f"{item.memory_id}:{item.kind}:{item.summary[:80]}" for item in memories) or "Nenhuma memoria curada ativa encontrada."
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok",
            message=f"Memorias curadas ativas: {summary}. Esta foi uma leitura explicita; memoria curada nao e injetada automaticamente no prompt.",
            next_actions=[ChatNextAction(type="search_curated_memory", label="Buscar memoria curada")],
            warnings=["explicit_memory_read", "no_auto_prompt_memory"],
        )

    def _extract_id(self, message: str, prefix: str) -> str | None:
        import re

        match = re.search(rf"({re.escape(prefix)}[A-Za-z0-9_]+)", message)
        return match.group(1) if match else None

    def _memory_candidate_from_chat(self, request: ChatRequest, session_id: str | None) -> ChatResponse | None:
        from aipinho.schemas.memory.memory_candidate import MemoryCandidateRequest, MemoryCandidateScope, MemoryCandidateSource
        from aipinho.services.memory.memory_candidate_service import MemoryCandidateService

        text = self._extract_memory_candidate_text(request.message)
        if not text:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Posso criar candidato de memoria, mas preciso de uma afirmacao curta, fonte clara e escopo. Nada sera persistido como memoria definitiva.",
                next_actions=[ChatNextAction(type="create_memory_candidate", label="Criar candidato de memoria com fonte e escopo")],
                warnings=["memory_candidate_requires_source_scope_evidence", "approved_memory_disabled"],
            )
        scope = MemoryCandidateScope(scope_type="user_instruction", workspace=request.context.active_workspace if request.context else None, reason="explicit_chat_memory_candidate_request")
        source = MemoryCandidateSource(source_type="user_instruction", source_id=session_id, source_ref=f"chat_session:{session_id}" if session_id else "chat_session", trusted=True)
        result = MemoryCandidateService().create_candidate(MemoryCandidateRequest(text=text, kind="user_instruction", source=source, scope=scope))
        candidate = result.candidate
        if candidate is None:
            return None
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status=candidate.status if candidate.status in {"blocked", "needs_review"} else "preview",
            message=f"Criei um candidato de memoria com status {candidate.status}. Ele esta pendente de aprovacao futura e nao foi persistido como memoria definitiva. Sem vectorstore/embedding nesta sprint.",
            next_actions=[
                ChatNextAction(type="view_memory_candidate", label="Ver candidato de memoria", target_id=candidate.candidate_id),
                ChatNextAction(type="reject_memory_candidate", label="Rejeitar candidato de memoria", target_id=candidate.candidate_id),
            ],
            warnings=list(dict.fromkeys([*candidate.warnings, *candidate.blocked_reasons, "candidate_only_memory", "chat_cannot_approve_memory"])),
        )

    def _memory_candidate_list_response(self, session_id: str | None) -> ChatResponse:
        from aipinho.services.memory.memory_candidate_service import MemoryCandidateService

        candidates = MemoryCandidateService().list_candidates(limit=10)
        summary = "; ".join(f"{item.candidate_id}:{item.status}:{item.kind}:{item.summary[:80]}" for item in candidates) or "Nenhum candidato de memoria encontrado."
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok",
            message=f"Candidatos de memoria atuais: {summary}. Eles nao sao memoria definitiva e dependem de aprovacao futura.",
            next_actions=[ChatNextAction(type="view_memory_candidates", label="Ver candidatos de memoria")],
            warnings=["candidate_only_memory", "approved_memory_disabled"],
        )

    def _extract_memory_candidate_text(self, message: str) -> str | None:
        import re

        patterns = [
            r"(?i)guarde como candidato\s*:\s*(.+)",
            r"(?i)isso deve virar mem[oó]ria depois\s*:\s*(.+)",
            r"(?i)guarde isso na mem[oó]ria\s*:\s*(.+)",
            r"(?i)registre como mem[oó]ria\s*:\s*(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, flags=re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _requests_artifact_preview(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"salve", "salvar", "grave", "gravar"}) and any(ext in lowered for ext in {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".html", ".py", ".js", ".ts", ".kt", ".ps1", ".bat", ".sh"})

    def _requests_artifact_write_now(self, message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in {"gravar agora", "grave agora", "salvar agora", "salve agora", "pode gravar agora"})

    def _requests_role_model_status(self, message: str) -> bool:
        lowered = message.lower()
        role_terms = {"role", "roles", "papel", "papeis", "papéis"}
        model_terms = {"modelo", "modelos", "role-model", "role-models", "binding", "vinculo", "vinculo", "vinculado", "vinculados"}
        catalog_terms = {"quais", "listar", "liste", "status", "health", "ligado", "ligados", "configurado", "configurados"}
        return any(term in lowered for term in role_terms) and any(term in lowered for term in model_terms) and any(term in lowered for term in catalog_terms)

    def _requests_role_model_run(self, message: str) -> bool:
        lowered = message.lower()
        role_terms = {"role", "roles", "papel", "papeis", "papéis"}
        model_terms = {"modelo", "modelos", "gguf", "qwen", "deepseek", "14b", "7b"}
        execution_terms = {"use", "usar", "rode", "rodar", "execute", "executar", "inferencia", "inferência", "gerar", "gere"}
        return any(term in lowered for term in role_terms) and any(term in lowered for term in model_terms) and any(term in lowered for term in execution_terms)

    def _requests_role_model_14b(self, message: str) -> bool:
        lowered = message.lower()
        execution_terms = {"use", "usar", "rode", "rodar", "execute", "executar", "inferencia", "inferência", "ativar"}
        return "14b" in lowered and any(term in lowered for term in execution_terms)

    def _role_model_status_response(self, session_id: str | None) -> ChatResponse:
        status = RoleModelStatusService().status()
        roles = status.get("roles", []) if isinstance(status.get("roles", []), list) else []
        default_role = status.get("default_coding_role", "coder")
        default_model = status.get("default_coding_model", "qwen2_5_coder_7b_q4_k_m")
        role_summary = ", ".join(str(item.get("role_id")) for item in roles[:8] if isinstance(item, dict) and item.get("role_id"))
        if len(roles) > 8:
            role_summary = f"{role_summary}, ..."
        message = (
            f"Inferencia controlada por role esta configurada para {len(roles)} roles. "
            f"Default de codigo: {default_role} -> {default_model}. "
            f"Roles visiveis: {role_summary or 'nenhum'}. "
            "O chat pode usar inferencia real governada por role quando a policy permitir; execucao com efeito colateral continua passando pelos gates."
        )
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="ok",
            message=message,
            next_actions=[
                ChatNextAction(type="view_role_model_status", label="Ver status role-model"),
                ChatNextAction(type="preview_role_model_run", label="Preview por role"),
            ],
            warnings=["role_model_inference_governed", "side_effects_require_policy_gate"],
            model_used=str(status.get("default_coding_model") or "qwen2_5_coder_7b_q4_k_m"),
            real_inference=bool(status.get("chat_auto_role_inference", False)),
        )

    def _role_model_14b_block_response(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="blocked",
            message=(
                "Modelos 14B sao manual-only. O chat nao pode iniciar esse uso automaticamente. "
                "Use o endpoint explicito de role-model com manual_escalation=true, operator_confirmed=true, "
                "latency_warning_acknowledged=true e uma justificativa."
            ),
            next_actions=[ChatNextAction(type="manual_role_model_escalation", label="Usar endpoint explicito")],
            warnings=["large_model_manual_only", "operator_confirmation_required"],
            model_used="stub.default",
            real_inference=False,
        )

    def _public_fact_query_response(self, session_id: str | None, decision: Any) -> ChatResponse:
        result = self.web_search_provider.search(decision.primary_prompt or "", max_results=3)
        trace = [
            ChatTraceItem(
                stage="intent_classified",
                status="ok",
                reason="public_fact_query",
                source="services/chat/chat_operation_router_service.py",
                data={"operation_id": decision.operation_id, "intent_type": "public_fact_query"},
            ),
            ChatTraceItem(
                stage="web_provider_called",
                status=result.status,
                reason=result.reason_code or "web_search_provider_result",
                source="services/web_search_provider_service.py",
                data={"provider_id": result.provider_id, "source_count": result.source_count},
            ),
        ]
        if result.status == "ready" and result.results:
            summary = WebSearchSummaryService().summarize(
                query=decision.primary_prompt or "",
                sources=result.results,
            )
            sources = "\n".join(f"- [{idx}] {source.title} — {source.url}" for idx, source in enumerate(result.results, start=1))
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="ready",
                message=(
                    "Pesquisa pública executada com fontes.\n\n"
                    "Resumo:\n"
                    f"{summary.text}\n\n"
                    "Fontes:\n"
                    f"{sources}"
                ),
                intent={
                    "intent_type": "public_fact_query",
                    "requires_task": False,
                    "requires_workspace": False,
                    "requires_web_search": True,
                    "private_rag_required": False,
                },
                policy={"status": "allowed", "provider_scope": "web_search", "source_count": result.source_count},
                operation_id=decision.operation_id,
                operation_type="web_search_required",
                message_type="assistant_final_answer",
                warnings=list(dict.fromkeys([*(result.warnings or []), *summary.warnings])),
                trace=trace,
                is_final_answer=True,
                grounded=True,
                grounding_required=True,
                citation_map={
                    "sources": [source.model_dump() for source in result.results],
                    "provider_id": result.provider_id,
                    "searched_at": result.searched_at,
                },
                evidence_refs=[
                    {"type": "web_source", "ref_id": str(idx), "human_label": source.title, "url": source.url}
                    for idx, source in enumerate(result.results, start=1)
                ],
            )

        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="blocked",
            message=(
                "Essa pergunta parece depender de conhecimento publico verificavel. "
                "O fluxo correto e acionar Web/Search Provider com fontes; nesta instalacao o provider esta desabilitado ou indisponivel."
            ),
            intent={
                "intent_type": "public_fact_query",
                "requires_task": False,
                "requires_workspace": False,
                "requires_web_search": True,
                "private_rag_required": False,
            },
            policy={
                "status": "capability_missing" if result.status == "capability_missing" else result.status,
                "reason_code": result.reason_code or "web_search_provider_failed",
                "required_capability": "web_search",
            },
            operation_id=decision.operation_id,
            operation_type="web_search_required",
            message_type="blocked_policy_message",
            warnings=list(dict.fromkeys(["CAPABILITY_MISSING", *(result.warnings or []), result.reason_code or "web_search_provider_failed"])),
            next_actions=[ChatNextAction(type="configure_web_search_provider", label="Configurar Web/Search Provider")],
            requires_user_action=True,
            is_final_answer=False,
            grounded=False,
            grounding_required=True,
            grounding_missing_reason=result.reason_code or "web_search_provider_failed",
            trace=trace,
            evidence_refs=[
                {"type": "capability", "ref_id": "web_search", "human_label": "Web/Search Provider"}
            ],
        )

    def _blocked_operation_response(self, session_id: str | None, decision: Any) -> ChatResponse:
        reason_code = "dangerous_operation_blocked"
        if "git" in str(decision.primary_prompt or "").casefold():
            reason_code = "git_write_blocked"
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="blocked",
            message=(
                "Bloqueei este pedido antes de executar qualquer acao local. "
                "Ele envolve uma operacao destrutiva, irreversivel ou de escrita Git que exige um contrato governado especifico."
            ),
            intent={
                "intent_type": "dangerous_operation",
                "requires_task": False,
                "requires_workspace": bool(decision.workspace),
                "requested_operation": decision.operation_type,
            },
            policy={
                "status": "denied",
                "reason_code": reason_code,
                "policy_name": "dangerous_operation_policy",
                "safe_to_execute": False,
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="blocked_policy_message",
            requires_user_action=True,
            is_final_answer=False,
            warnings=[reason_code],
            evidence_refs=[{"type": "policy", "ref_id": reason_code, "human_label": "Policy block"}],
        )

    def _attachment_required_missing_response(self, session_id: str | None, decision: Any) -> ChatResponse:
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="blocked",
            message=(
                "Este pedido declara que um anexo e obrigatorio, mas nenhum contexto de anexo chegou ao backend. "
                "Envie o arquivo ou remova a exigencia de anexo para continuar."
            ),
            intent={
                "intent_type": "attachment_required_request",
                "requires_task": False,
                "requires_workspace": bool(decision.workspace),
            },
            policy={
                "status": "blocked",
                "reason_code": "attachment_required_missing",
                "safe_to_execute": False,
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="blocked_policy_message",
            requires_user_action=True,
            is_final_answer=False,
            warnings=["attachment_required_missing"],
            next_actions=[ChatNextAction(type="attach_file", label="Enviar anexo")],
        )

    def _sandbox_writer_response(self, session_id: str | None, prompt: str, decision: Any) -> ChatResponse | None:
        path_ref = self._resolve_sandbox_operation_path(session_id, decision)
        if decision.operation_type == "sandbox_capability_test":
            result = self.sandbox_writer.capability_probe(content="AIpinho confirmou escrita governada em sandbox.\n")
        elif not path_ref and decision.metadata.get("requires_context_path"):
            return self._context_path_missing_response(session_id, decision)
        elif not self.sandbox_writer.is_sandbox_path(path_ref):
            return None
        elif decision.operation_type == "filesystem_create_directory":
            result = self.sandbox_writer.create_directory(path_ref=path_ref or "")
        elif decision.operation_type == "filesystem_read_file":
            result = self.sandbox_writer.read_text_file(path_ref=path_ref or "")
        elif decision.operation_type == "filesystem_append_file":
            result = self.sandbox_writer.append_text_file(
                path_ref=path_ref or "",
                content=self.sandbox_writer.extract_text_content(prompt),
            )
        elif decision.operation_type == "sandbox_batch_artifact_request":
            result = self.sandbox_writer.create_text_bundle_archive(path_ref=path_ref or "", prompt=prompt)
        else:
            result = self.sandbox_writer.write_text_file(
                path_ref=path_ref or "",
                content=self.sandbox_writer.extract_text_content(prompt),
                overwrite=False,
            )
        trace = [
            ChatTraceItem(
                stage="intent_classified",
                status="ok",
                reason=decision.operation_type,
                source="services/chat/chat_operation_router_service.py",
                data={"operation_id": decision.operation_id},
            ),
            ChatTraceItem(
                stage="sandbox_writer_called",
                status=result.status,
                reason=result.reason_code or "sandbox_writer_result",
                source="services/sandbox_file_writer_service.py",
                data={"run_id": result.run_id, "path": result.path, "size_bytes": result.size_bytes},
            ),
        ]
        if result.status == "ready":
            file_excerpt = self._sandbox_file_excerpt(result)
            if result.operation_type == "filesystem_read_file":
                human_message = (
                    "Li o arquivo solicitado em modo governado de sandbox.\n\n"
                    f"Arquivo: {result.path}\n"
                    f"Tamanho: {result.size_bytes} bytes\n\n"
                    f"Conteudo:\n{file_excerpt}"
                )
            elif result.operation_type == "sandbox_capability_test":
                human_message = (
                    "Consegui executar um teste real de escrita governada em sandbox.\n\n"
                    f"Arquivo de prova: {result.path}\n"
                    f"Validacao: {'conteudo validado' if result.content_validated else 'pendente'}"
                )
            else:
                evidence_text = "\n".join(f"- {item.kind}: {item.status}" for item in result.evidence)
                if result.operation_type == "sandbox_batch_artifact_request":
                    human_message = (
                        "READY\n\n"
                        f"TASK: {result.run_id}\n"
                        f"OPERATION: {result.operation_type}\n"
                        f"ARTEFATO: {result.path}\n"
                        f"TAMANHO: {result.size_bytes} bytes\n"
                        f"VALIDACAO: {'zip validado' if result.content_validated else 'pendente'}\n\n"
                        "EVIDENCIAS:\n"
                        f"{evidence_text}"
                    )
                else:
                    human_message = (
                        "READY\n\n"
                        f"TASK: {result.run_id}\n"
                        f"OPERATION: {result.operation_type}\n"
                        f"ARQUIVO: {result.path}\n"
                        f"TAMANHO: {result.size_bytes} bytes\n"
                        f"VALIDACAO: {'conteudo validado' if result.content_validated else 'pendente'}\n\n"
                        "EVIDENCIAS:\n"
                        f"{evidence_text}"
                    )
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                task_id=result.run_id,
                status="ready",
                message=human_message,
                intent={
                    "intent_type": "filesystem_read_request" if result.operation_type == "filesystem_read_file" else "filesystem_write_request",
                    "requires_task": True,
                    "requires_workspace": True,
                    "requested_operation": result.operation_type,
                },
                policy={
                    "status": "allowed",
                    "policy_decision": result.policy_decision,
                    "approval_decision": result.approval_decision,
                    "workspace_decision": "allowed_sandbox",
                    "safe_to_execute": True,
                    "path": result.path,
                },
                operation_id=decision.operation_id,
                operation_type=result.operation_type,
                message_type="assistant_final_answer",
                is_final_answer=True,
                grounded=True,
                trace=trace,
                evidence_refs=[
                    {"type": item.kind, "ref_id": item.evidence_id, "human_label": item.status, **item.details}
                    for item in result.evidence
                ],
                warnings=result.warnings,
            )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=result.run_id,
            status="failed" if result.status == "failed" else "blocked",
            message=f"A escrita em sandbox nao foi concluida. Motivo: {result.reason_code or 'sandbox_writer_failed'}.",
            intent={
                "intent_type": "filesystem_write_request",
                "requires_task": True,
                "requires_workspace": True,
                "requested_operation": result.operation_type,
            },
            policy={
                "status": result.status,
                "reason_code": result.reason_code,
                "policy_decision": result.policy_decision,
                "approval_decision": result.approval_decision,
            },
            operation_id=decision.operation_id,
            operation_type=result.operation_type,
            message_type="blocked_policy_message",
            is_final_answer=False,
            grounded=True,
            trace=trace,
            warnings=result.warnings or result.errors,
        )

    def _resolve_sandbox_operation_path(self, session_id: str | None, decision: Any) -> str | None:
        if decision.workspace:
            return decision.workspace
        if not session_id or not decision.metadata.get("requires_context_path"):
            return None
        state = self.session_service.get_session(session_id)
        if state is None:
            return None
        path = state.last_operational_context.get("path")
        return str(path) if path else None

    def _sandbox_file_excerpt(self, result: Any) -> str:
        for item in result.evidence:
            if item.kind == "file_excerpt":
                content = item.details.get("content")
                return str(content or "")
        return ""

    def _context_path_missing_response(self, session_id: str | None, decision: Any) -> ChatResponse:
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="blocked",
            message=(
                "Nao encontrei um arquivo recente seguro para aplicar este pedido. "
                "Informe o caminho do arquivo ou repita a operacao com um arquivo explicito."
            ),
            intent={
                "intent_type": "filesystem_write_request",
                "requires_task": False,
                "requires_workspace": True,
                "requested_operation": decision.operation_type,
            },
            policy={
                "status": "blocked",
                "reason_code": "context_path_missing",
                "safe_to_execute": False,
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="blocked_policy_message",
            is_final_answer=False,
            warnings=["context_path_missing"],
        )

    def _product_planning_readonly_response(self, session_id: str | None, decision: Any) -> ChatResponse:
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=(
                "PRODUCT_PLANNING_READONLY_READY\n\n"
                "Classifiquei este pedido como planejamento textual read-only. "
                "Nao criei grant, ApprovalRequest, TaskPreview, TaskRun, shell ou escrita de arquivos.\n\n"
                "Analise de produto:\n"
                "- O pedido deve ser tratado como descoberta e planejamento, com foco em objetivo, escopo, riscos, criterios de aceite e sequencia de sprints.\n"
                "- Termos de governanca citados no prompt sao requisitos/constraints do plano, nao autorizacoes para mutar configuracao.\n\n"
                "Plano de acao sugerido em sprints:\n"
                "1. Sprint de descoberta: mapear publico, problema, fluxo principal e restricoes.\n"
                "2. Sprint de blueprint: definir telas, dados, operacoes e contratos de seguranca.\n"
                "3. Sprint de MVP: decompor features em entregas pequenas e validaveis.\n"
                "4. Sprint de QA: validar UX, contratos, permissions e mensagens humanas.\n"
                "5. Sprint de hardening: fechar riscos, observabilidade e criterios de release.\n\n"
                "Proximo passo seguro: quando quiser executar, envie um pedido operacional separado com workspace e escopo de escrita; ai o fluxo deve criar preview e approval antes de qualquer side effect."
            ),
            intent={
                "intent_type": "product_planning_readonly",
                "requires_task": False,
                "requires_workspace": False,
                "requires_patch": False,
                "approval_required": False,
            },
            policy={
                "status": "read_only",
                "safe_to_execute": False,
                "side_effects_allowed": False,
                "approval_required_for": [],
                "write_allowed": False,
                "shell_allowed": False,
            },
            operation_id=decision.operation_id,
            operation_type="product_planning_readonly",
            message_type="assistant_final_answer",
            is_final_answer=True,
            grounded=True,
            warnings=[],
        )

    def _specific_operation_preview_response(self, session_id: str | None, decision: Any) -> ChatResponse:
        approval_scope = str(decision.metadata.get("approval_scope") or "policy_review")
        intent_type = {
            "filesystem_create_directory": "filesystem_write_request",
            "filesystem_write_file": "filesystem_write_request",
            "filesystem_modify_file": "file_modification_request",
            "project_create": "project_generation_request",
            "android_project_create": "android_project_generation",
            "project_bootstrap": "governed_project_bootstrap",
            "android_apk_build": "artifact_build_request",
            "artifact_build_request": "artifact_build_request",
        }.get(str(decision.metadata.get("router_operation_type") or decision.operation_type), "operational_task_request")
        workspace_policy = WorkspacePolicyService().load().evaluate(workspace_path=decision.workspace, requires_workspace=bool(decision.workspace))
        if workspace_policy.blocked:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="blocked",
                message=f"A operacao foi bloqueada pela policy do workspace. Motivo: {workspace_policy.reason}.",
                intent={
                    "intent_type": intent_type,
                    "requires_task": True,
                    "requires_workspace": bool(decision.workspace),
                    "requested_operation": decision.operation_type,
                },
                policy={
                    "status": "denied",
                    "reason_code": workspace_policy.reason,
                    "approval_required_for": [],
                    "safe_to_preview": False,
                    "safe_to_execute": False,
                },
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                message_type="blocked_policy_message",
                is_final_answer=False,
                grounded=True,
                warnings=[workspace_policy.reason],
                evidence_refs=[
                    {"type": "workspace_policy", "ref_id": workspace_policy.reason, "human_label": "Workspace policy"}
                ],
            )
        if decision.operation_type == "filesystem_create_directory":
            return self._directory_creation_approval_preview_response(session_id, decision, intent_type)
        if self._is_project_generation_operation(decision):
            return self._project_generation_approval_preview_response(session_id, decision, intent_type)
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="preview",
            message=(
                "Criei um preview operacional com escopo especifico. "
                "Nada foi executado ainda porque este pedido nao esta no caminho minimo de sandbox autoaprovada."
            ),
            intent={
                "intent_type": intent_type,
                "requires_task": True,
                "requires_workspace": bool(decision.workspace),
                "requested_operation": decision.operation_type,
            },
            policy={
                "status": "needs_approval_or_capability_check",
                "approval_required_for": [approval_scope],
                "safe_to_preview": True,
                "safe_to_execute": False,
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="task_preview",
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            grounding_missing_reason="task_preview_not_execution_result",
            next_actions=[ChatNextAction(type="review_operation_preview", label="Revisar preview operacional", target_id=decision.operation_id)],
            warnings=["operation_preview_only", f"approval_scope:{approval_scope}"],
        )

    def _directory_creation_approval_preview_response(self, session_id: str | None, decision: Any, intent_type: str) -> ChatResponse:
        target_path = str(decision.metadata.get("target_path") or decision.workspace or "")
        if not target_path:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="needs_clarification",
                message="Preciso do caminho alvo antes de criar o preview de diretorio. Nenhuma escrita foi executada.",
                intent={"intent_type": intent_type, "requires_task": True, "requires_workspace": True},
                policy={"status": "needs_workspace", "reason_code": "target_path_missing", "safe_to_execute": False},
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                message_type="clarification_request",
                requires_user_action=True,
                warnings=["target_path_missing"],
            )
        now = utc_now()
        approval_action = "create_directory"
        operation_contract = self.operation_contract_service.build(
            source_channel="chat",
            source_client="aipinho_chat",
            session_id=session_id,
            user_text=str(decision.primary_prompt or ""),
            intent_type=intent_type,
            operation_type=str(decision.operation_type),
            requested_actions=[approval_action],
            workspace_refs=[decision.workspace] if decision.workspace else [],
            target_paths=[target_path],
            operation_id=decision.operation_id,
        )
        denied_actions = [item.action for item in operation_contract.permission_decisions if item.decision == "denied"]
        if denied_actions:
            reason = operation_contract.warnings[0] if operation_contract.warnings else "policy_denied"
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="blocked",
                message=(
                    "Pedido bloqueado pela Policy Kernel antes do approval.\n"
                    f"Motivo: {reason}.\n"
                    f"Operacao: {decision.operation_type}.\n"
                    f"Workspace: {decision.workspace or 'nao resolvido'}.\n"
                    f"Acoes solicitadas: {approval_action}.\n"
                    "ApprovalRequest criado: nao, porque a policy retornou denied."
                ),
                intent={"intent_type": intent_type, "requires_task": True, "requires_workspace": bool(decision.workspace)},
                policy={
                    "status": "denied",
                    "reason_code": reason,
                    "approval_required_for": [],
                    "denied_actions": denied_actions,
                    "safe_to_preview": False,
                    "safe_to_execute": False,
                    "next_action": "revise_workspace_or_request_policy_change",
                },
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                message_type="blocked_policy_message",
                is_final_answer=False,
                grounded=True,
                warnings=list(operation_contract.warnings or [reason]),
            )
        draft = TaskContractDraft(
            draft_id=f"directory_create_{uuid4().hex}",
            session_id=session_id,
            status="approval_required" if operation_contract.approval_required else "draft",
            intent_map={
                "prompt": decision.primary_prompt,
                "source_channel": "chat",
                "intent": intent_type,
                "risk": "medium",
                "requested_operation": "create_directory",
                "target_path": target_path,
                "target_paths": [target_path],
                "requested_actions": [approval_action],
                "concrete_file_operations": [{"action": approval_action, "target_path": target_path}],
                "operation_contract": operation_contract.model_dump(),
            },
            policy_decision={
                "decision_id": f"directory_create_policy_{uuid4().hex}",
                "status": "needs_approval" if operation_contract.approval_required else "preview_ready",
                "allowed_actions": [],
                "denied_actions": [],
                "approval_required_for": [approval_action] if operation_contract.approval_required else [],
                "granted_capabilities": [],
                "denied_capabilities": [],
                "operation_contract_id": operation_contract.operation_id,
            },
            contract_type="filesystem_write",
            operation_type="filesystem_create_directory",
            intent_type=intent_type,
            runtime_profile="write_file",
            capabilities_required=["workspace_write", "validation"],
            source_scope="chat",
            requires_workspace=True,
            workspace=TaskDraftWorkspace(path=decision.workspace or target_path, status="confirmed"),
            requested_actions=[approval_action],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=[approval_action] if operation_contract.approval_required else [],
            executable_plan_ref=f"concrete_file_operations:{decision.operation_id}",
            expected_outcomes=["filesystem_operation", "validation_result"],
            safe_to_execute=False,
            safe_to_preview=True,
            warnings=list(operation_contract.warnings),
            trace=[
                {
                    "source": "services/chat/chat_service.py",
                    "stage": "directory_creation_approval_preview",
                    "decision": "approval_required" if operation_contract.approval_required else "preview_ready",
                    "reason": "directory_creation_requires_preview_approval_before_execution",
                    "operation_id": decision.operation_id,
                    "operation_contract_id": operation_contract.operation_id,
                }
            ],
            created_at=now,
            updated_at=now,
        )
        self.task_draft_service.store.save(draft)
        self.task_draft_service.append_event(
            draft.draft_id,
            "draft_created",
            "Draft de criacao de diretorio criado pelo chat; nenhuma escrita foi executada.",
            {"operation_id": decision.operation_id, "target_path": target_path, "requested_action": approval_action},
        )
        preview = self.task_preview_service.create_preview_from_draft(draft.draft_id)
        approval = None
        if preview is not None and preview.status == "approval_required":
            approval = self.approval_service.create_approval_for_preview(
                preview.preview_id,
                actions=[approval_action],
                reason="Directory creation requires approval before filesystem write execution",
            )
        status = "pending_approval" if approval is not None else "preview"
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=draft.draft_id,
            approval_id=approval.approval_id if approval else None,
            preview_id=preview.preview_id if preview else None,
            status=status,
            message=(
                "DIRECTORY_CREATION_PENDING_APPROVAL\n\n"
                f"Target: {target_path}\n"
                f"Approval: {approval.approval_id if approval else 'nao criado'}\n"
                f"Preview: {preview.preview_id if preview else 'nao criado'}\n"
                "Nenhuma pasta foi criada antes da aprovacao.\n"
                f"Para aprovar: APROVAR {approval.approval_id if approval else '<approval_id>'}"
            ),
            intent={"intent_type": intent_type, "requires_task": True, "requires_workspace": True, "requested_operation": "create_directory"},
            policy={
                "status": "needs_approval" if approval else "preview_ready",
                "approval_required_for": [approval_action] if approval else [],
                "safe_to_preview": True,
                "safe_to_execute": False,
                "target_path": target_path,
                "reason_code": "approval_required" if approval else "preview_created_without_approval",
                "operation_contract_id": operation_contract.operation_id,
            },
            contract_preview={
                "draft": draft.model_dump(),
                "preview": preview.model_dump() if preview else None,
                "approval": approval.model_dump() if approval else None,
                "operation_contract": operation_contract.model_dump(),
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="task_preview",
            requires_user_action=approval is not None,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            warnings=["directory_creation_preview_only", *list(operation_contract.warnings)],
        )

    def _is_project_generation_operation(self, decision: Any) -> bool:
        router_operation = str(decision.metadata.get("router_operation_type") or "")
        return str(decision.operation_type) in {"project_create", "android_project_create", "project_generation", "governed_project_rebuild", "logforge_mobile_implementation"} or router_operation in {
            "project_create",
            "android_project_create",
            "governed_project_rebuild",
            "project_bootstrap",
        }

    def _project_generation_approval_preview_response(self, session_id: str | None, decision: Any, intent_type: str) -> ChatResponse:
        if not decision.workspace:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="needs_clarification",
                message="Preciso do workspace alvo antes de criar o approval de geracao/implementacao do projeto.",
                intent={
                    "intent_type": intent_type,
                    "requires_task": True,
                    "requires_workspace": True,
                    "requested_operation": decision.operation_type,
                },
                policy={
                    "status": "needs_workspace",
                    "approval_required_for": [],
                    "safe_to_preview": False,
                    "safe_to_execute": False,
                },
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                message_type="clarification_request",
                requires_user_action=True,
                is_final_answer=False,
                grounded=True,
                warnings=["target_workspace_missing"],
            )
        now = utc_now()
        approval_action = "write_files"
        router_operation = str(decision.metadata.get("router_operation_type") or "")
        pre_approval_expected = list(
            decision.metadata.get("pre_approval_expected_outcomes", [])
            or ["project_generation", "validation_result"]
        )
        contract_user_text = str(decision.primary_prompt or "")
        if router_operation == "project_bootstrap":
            contract_user_text = (
                "Criar blueprint, TaskPreview e ApprovalRequest para bootstrap governado de projeto. "
                "Qualquer escrita futura deve aguardar approval explicito."
            )
        operation_contract = self.operation_contract_service.build(
            source_channel="chat",
            source_client="aipinho_chat",
            session_id=session_id,
            user_text=contract_user_text,
            intent_type=intent_type,
            operation_type=str(decision.operation_type),
            requested_actions=[approval_action],
            workspace_refs=[decision.workspace],
            target_paths=[decision.workspace],
            operation_id=decision.operation_id,
        )
        denied_actions = [
            item.action
            for item in operation_contract.permission_decisions
            if item.decision == "denied"
        ]
        if denied_actions:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="blocked",
                message=(
                    "Pedido bloqueado pela policy antes do approval porque a acao foi negada. "
                    f"Motivo: {', '.join(operation_contract.warnings) or 'policy_denied'}."
                ),
                intent={
                    "intent_type": intent_type,
                    "requires_task": True,
                    "requires_workspace": True,
                    "requested_operation": decision.operation_type,
                },
                policy={
                    "status": "denied",
                    "approval_required_for": [],
                    "denied_actions": denied_actions,
                    "reason_code": operation_contract.warnings[0] if operation_contract.warnings else "policy_denied",
                    "safe_to_preview": False,
                    "safe_to_execute": False,
                    "operation_contract_id": operation_contract.operation_id,
                },
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                message_type="blocked_policy_message",
                is_final_answer=False,
                grounded=True,
                warnings=list(operation_contract.warnings or ["policy_denied"]),
            )
        project_generation_plan = {
            "target_workspace": decision.workspace,
            "stack_detected": str(decision.metadata.get("stack_detected") or "unknown"),
            "entrypoints": list(decision.metadata.get("entrypoints", []) or []),
            "files_to_create": list(decision.metadata.get("files_to_create", []) or []),
            "files_to_modify": list(decision.metadata.get("files_to_modify", []) or []),
            "generation_steps": [
                "inspect_workspace_state",
                "derive_file_operations_from_user_goal",
                "create_or_modify_files_through_governed_runtime",
                "record_generated_files",
            ],
            "report_files": list(decision.metadata.get("report_files", []) or []),
            "validation_steps": [
                "verify_generated_or_modified_files",
                "verify_no_write_outside_workspace",
                "record_validation_result",
            ],
            "expected_outputs": pre_approval_expected,
            "negative_constraints": list(decision.metadata.get("negative_constraints", []) or []),
            "bootstrap_title": decision.metadata.get("bootstrap_title"),
        }
        draft = TaskContractDraft(
            draft_id=f"project_generation_{uuid4().hex}",
            session_id=session_id,
            status="approval_required" if operation_contract.approval_required else "draft",
            intent_map={
                "prompt": decision.primary_prompt,
                "source_channel": "chat",
                "intent": intent_type,
                "risk": "medium",
                "requested_operation": decision.operation_type,
                "target_path": decision.workspace,
                "requested_actions": list(decision.metadata.get("requested_actions", []) or [approval_action]),
                "operation_contract": operation_contract.model_dump(),
                "project_generation_plan": project_generation_plan,
            },
            policy_decision={
                "decision_id": f"project_generation_policy_{uuid4().hex}",
                "status": "needs_approval" if operation_contract.approval_required else "preview_ready",
                "allowed_actions": [],
                "denied_actions": [],
                "approval_required_for": [approval_action] if operation_contract.approval_required else [],
                "granted_capabilities": [],
                "denied_capabilities": [],
                "operation_contract_id": operation_contract.operation_id,
            },
            contract_type="project_generation",
            operation_type=str(decision.operation_type),
            intent_type=intent_type,
            runtime_profile="project_generation",
            capabilities_required=["read_workspace", "workspace_write", approval_action, "validation"],
            source_scope="chat",
            requires_workspace=True,
            workspace=TaskDraftWorkspace(path=decision.workspace, status="confirmed"),
            requested_actions=[approval_action],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=[approval_action] if operation_contract.approval_required else [],
            executable_plan_ref=f"project_generation_plan:{decision.operation_id}",
            expected_outcomes=pre_approval_expected,
            safe_to_execute=False,
            safe_to_preview=True,
            warnings=list(operation_contract.warnings),
            trace=[
                {
                    "source": "services/chat/chat_service.py",
                    "stage": "project_generation_approval_bootstrap",
                    "decision": "approval_required" if operation_contract.approval_required else "preview_ready",
                    "reason": "project_generation_requires_preview_approval_before_execution",
                    "operation_id": decision.operation_id,
                    "operation_contract_id": operation_contract.operation_id,
                }
            ],
            created_at=now,
            updated_at=now,
        )
        self.task_draft_service.store.save(draft)
        self.task_draft_service.append_event(
            draft.draft_id,
            "draft_created",
            "Draft de geracao/implementacao de projeto criado pelo chat; nenhuma escrita foi executada.",
            {"operation_id": decision.operation_id, "requested_action": approval_action},
        )
        preview = self.task_preview_service.create_preview_from_draft(draft.draft_id)
        approval = None
        if preview is not None and preview.status == "approval_required":
            approval = self.approval_service.create_approval_for_preview(
                preview.preview_id,
                actions=[approval_action],
                reason="Project generation requires approval before workspace write execution",
            )
            self.approval_service.append_event(
                approval.approval_id,
                "approval_request_created",
                "ApprovalRequest de geracao/implementacao de projeto criado pelo chat.",
                {
                    "source_channel": "chat",
                    "session_id": session_id,
                    "operation_id": decision.operation_id,
                    "preview_id": preview.preview_id,
                    "approval_id": approval.approval_id,
                    "action_type": approval_action,
                },
            )
        status = "pending_approval" if approval is not None else "preview"
        status_label = "PROJECT_BOOTSTRAP_PENDING_APPROVAL" if router_operation == "project_bootstrap" else "PROJECT_GENERATION_PENDING_APPROVAL"
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=draft.draft_id,
            preview_id=preview.preview_id if preview else None,
            task_preview_id=preview.preview_id if preview else None,
            approval_id=approval.approval_id if approval else None,
            status=status,
            message=(
                f"STATUS: {status_label}\n\n"
                "Criei um preview operacional real para a geracao/implementacao do projeto. Nada foi executado ainda.\n\n"
                f"approval_id: {approval.approval_id if approval else 'nao_requerido'}\n"
                f"acao: {approval_action}\n"
                f"workspace: {decision.workspace}\n"
                f"preview: {preview.preview_id if preview else 'preview_nao_criado'}\n\n"
                f"Para aprovar: APROVAR {approval.approval_id if approval else '<approval_id>'}"
            ),
            intent={
                "intent_type": intent_type,
                "requires_task": True,
                "requires_workspace": True,
                "requested_operation": decision.operation_type,
            },
            policy={
                "status": "needs_approval" if approval else "preview_ready",
                "approval_required_for": [approval_action] if approval else [],
                "safe_to_preview": True,
                "safe_to_execute": False,
                "operation_contract_id": operation_contract.operation_id,
            },
            contract_preview={
                "draft": draft.model_dump(),
                "preview": preview.model_dump() if preview else None,
                "approval": approval.model_dump() if approval else None,
                "operation_contract": operation_contract.model_dump(),
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="task_preview",
            requires_user_action=approval is not None,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            grounding_missing_reason="task_preview_not_execution_result",
            next_actions=[
                *(
                    [ChatNextAction(type="review_approval", label="Revisar aprovacao", target_id=approval.approval_id)]
                    if approval
                    else []
                ),
                ChatNextAction(type="view_task_preview", label="Ver preview operacional", target_id=preview.preview_id if preview else draft.draft_id),
            ],
            evidence_refs=[
                {"type": "task_draft", "ref_id": draft.draft_id, "human_label": "Draft de projeto governado"},
                *(
                    [{"type": "task_preview", "ref_id": preview.preview_id, "human_label": "Preview de projeto governado"}]
                    if preview
                    else []
                ),
                *(
                    [{"type": "approval_request", "ref_id": approval.approval_id, "human_label": "Approval de projeto governado"}]
                    if approval
                    else []
                ),
            ],
            warnings=["project_generation_preview_only", *list(operation_contract.warnings)],
        )

    def _governed_write_approval_response(
        self,
        session_id: str | None,
        prompt: str,
        decision: Any,
        *,
        workspace_ref: str | None,
        base_response: ChatResponse,
    ) -> ChatResponse:
        now = utc_now()
        action = "write_files"
        requested_operation = str(decision.metadata.get("requested_operation") or "create_file")
        filename = self.governed_write_service.planner.extract_requested_filename(prompt)
        operation_contract = self.operation_contract_service.build(
            source_channel="chat",
            source_client="aipinho_chat",
            session_id=session_id,
            user_text=prompt,
            intent_type="governed_file_write",
            operation_type=action,
            requested_actions=[action],
            workspace_refs=[workspace_ref] if workspace_ref else [],
            target_paths=[filename] if filename else [],
            content=str(decision.metadata.get("content") or ""),
            operation_id=decision.operation_id,
        )
        workspace = TaskDraftWorkspace(
            path=workspace_ref,
            status="confirmed" if workspace_ref else "missing",
        )
        draft = TaskContractDraft(
            draft_id=f"chat_write_{uuid4().hex}",
            session_id=session_id,
            status="approval_required" if workspace_ref else "needs_clarification",
            intent_map={
                "prompt": prompt,
                "source_channel": "chat",
                "intent": "governed_file_write",
                "risk": "medium",
                "requested_operation": requested_operation,
                "target_path": filename,
                "operation_contract": operation_contract.model_dump(),
            },
            policy_decision={
                "decision_id": f"chat_write_policy_{uuid4().hex}",
                "status": "needs_approval" if operation_contract.approval_required else ("blocked" if operation_contract.warnings else "allowed"),
                "allowed_actions": [],
                "denied_actions": [item.action for item in operation_contract.permission_decisions if item.decision == "denied"],
                "approval_required_for": [action] if operation_contract.approval_required else [],
                "granted_capabilities": [],
                "denied_capabilities": [],
                "operation_contract_id": operation_contract.operation_id,
            },
            contract_type="patch_request",
            operation_type=action,
            intent_type="governed_file_write",
            runtime_profile="write_file",
            capabilities_required=[action, "workspace_write"],
            source_scope="chat",
            requires_workspace=True,
            workspace=workspace,
            requested_actions=[action],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=[action] if operation_contract.approval_required else [],
            safe_to_execute=False,
            safe_to_preview=bool(workspace_ref),
            clarifying_questions=[] if workspace_ref else ["Informe um workspace target_mutable para a escrita governada."],
            warnings=list(dict.fromkeys([*operation_contract.warnings, *([] if workspace_ref else ["target_workspace_missing"])])),
            trace=[
                {
                    "source": "services/chat/chat_service.py",
                    "stage": "governed_write_approval",
                    "decision": "approval_required" if workspace_ref else "needs_clarification",
                    "reason": "workspace_write_requires_preview_approval_validation",
                    "operation_id": decision.operation_id,
                    "operation_contract_id": operation_contract.operation_id,
                }
            ],
            created_at=now,
            updated_at=now,
        )
        self.task_draft_service.store.save(draft)
        self.task_draft_service.append_event(
            draft.draft_id,
            "draft_created",
            "Draft de escrita governada criado pelo chat; nenhuma escrita foi realizada.",
            {"operation_id": decision.operation_id, "requested_action": action},
        )
        preview = self.task_preview_service.create_preview_from_draft(draft.draft_id)
        if preview is None or preview.status != "approval_required":
            return base_response.model_copy(
                update={
                    "warnings": list(dict.fromkeys([*base_response.warnings, "write_approval_preview_not_created"])),
                    "contract_preview": {
                        "draft": draft.model_dump(),
                        "preview": preview.model_dump() if preview else None,
                        "operation_contract": operation_contract.model_dump(),
                    },
                }
            )
        approval = self.approval_service.create_approval_for_preview(
            preview.preview_id,
            actions=[action],
            reason="Chat requested governed workspace write approval",
        )
        self.approval_service.append_event(
            approval.approval_id,
            "approval_request_created",
            "ApprovalRequest de escrita governada criado pelo chat.",
            {
                "source_channel": "chat",
                "session_id": session_id,
                "operation_id": decision.operation_id,
                "preview_id": preview.preview_id,
                "approval_id": approval.approval_id,
                "action_type": action,
            },
        )
        return base_response.model_copy(
            update={
                "preview_id": preview.preview_id,
                "approval_id": approval.approval_id,
                "policy": {
                    **base_response.policy,
                    "status": "needs_approval",
                    "approval_required_for": [action],
                    "safe_to_preview": True,
                    "safe_to_execute": False,
                },
                "evidence_refs": [
                    *base_response.evidence_refs,
                    {"type": "task_preview", "ref_id": preview.preview_id, "human_label": "Preview de escrita governada"},
                    {"type": "approval_request", "ref_id": approval.approval_id, "human_label": "Approval de escrita governada"},
                ],
                "next_actions": [
                    ChatNextAction(type="review_approval", label="Revisar aprovacao", target_id=approval.approval_id),
                    ChatNextAction(type="reject", label="Negar acao governada", target_id=approval.approval_id),
                ],
                "contract_preview": {
                    "draft": draft.model_dump(),
                    "preview": preview.model_dump(),
                    "approval": approval.model_dump(),
                    "operation_contract": operation_contract.model_dump(),
                },
            }
        )

    def _governed_shell_preview_response(
        self,
        session_id: str | None,
        prompt: str,
        decision: Any,
        *,
        workspace_ref: str | None,
    ) -> ChatResponse:
        now = utc_now()
        action = "run_command"
        command_text = str(decision.metadata.get("command_text") or prompt)
        operation_contract = self.operation_contract_service.build(
            source_channel="chat",
            source_client="aipinho_chat",
            session_id=session_id,
            user_text=prompt,
            intent_type="governed_shell_request",
            operation_type=action,
            requested_actions=[action],
            workspace_refs=[workspace_ref] if workspace_ref else [],
            command=command_text,
            operation_id=decision.operation_id,
        )
        workspace = TaskDraftWorkspace(
            path=workspace_ref,
            status="confirmed" if workspace_ref else "not_required",
        )
        draft = TaskContractDraft(
            draft_id=f"chat_shell_{uuid4().hex}",
            session_id=session_id,
            status="approval_required",
            intent_map={
                "prompt": prompt,
                "source_channel": "chat",
                "intent": "governed_shell_request",
                "risk": "high",
                "command_text": command_text,
                "operation_contract": operation_contract.model_dump(),
            },
            policy_decision={
                "decision_id": f"chat_shell_policy_{uuid4().hex}",
                "status": "needs_approval",
                "allowed_actions": [],
                "denied_actions": [item.action for item in operation_contract.permission_decisions if item.decision == "denied"],
                "approval_required_for": [action] if operation_contract.approval_required else [],
                "granted_capabilities": [],
                "denied_capabilities": [],
                "operation_contract_id": operation_contract.operation_id,
            },
            contract_type="validation_request",
            operation_type=action,
            intent_type="governed_shell_request",
            runtime_profile="governed",
            capabilities_required=[action, "shell"],
            source_scope="chat",
            requires_workspace=bool(workspace_ref),
            workspace=workspace,
            requested_actions=[action],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=[action] if operation_contract.approval_required else [],
            safe_to_execute=False,
            safe_to_preview=True,
            clarifying_questions=[],
            warnings=list(dict.fromkeys([*operation_contract.warnings, *([] if workspace_ref else ["workspace_must_be_resolved_before_execution"])])),
            trace=[
                {
                    "source": "services/chat/chat_service.py",
                    "stage": "governed_shell_preview",
                    "decision": "approval_required",
                    "reason": "shell_side_effect_requires_preview_approval_validation",
                    "operation_id": decision.operation_id,
                    "operation_contract_id": operation_contract.operation_id,
                }
            ],
            created_at=now,
            updated_at=now,
        )
        self.task_draft_service.store.save(draft)
        self.task_draft_service.append_event(
            draft.draft_id,
            "draft_created",
            "Draft de shell governado criado pelo chat; nenhuma execucao foi realizada.",
            {"operation_id": decision.operation_id, "requested_action": action},
        )
        preview = self.task_preview_service.create_preview_from_draft(draft.draft_id)
        if preview is None:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="failed",
                message="Nao consegui criar preview para o comando governado. Nenhum shell foi executado.",
                intent={"intent_type": "governed_shell_request", "requires_task": True, "requires_workspace": bool(workspace_ref)},
                policy={"status": "failed", "reason_code": "shell_preview_generation_failed", "safe_to_execute": False},
                operation_id=decision.operation_id,
                operation_type="governed_shell_request",
                message_type="assistant_degraded_answer",
                is_final_answer=False,
                grounded=True,
                warnings=["shell_preview_generation_failed"],
            )
        approval = self.approval_service.create_approval_for_preview(
            preview.preview_id,
            actions=[action],
            reason="Chat requested governed shell execution approval",
        )
        approval.commands = [command_text]
        self.approval_service.store.save(approval)
        self.approval_service.append_event(
            approval.approval_id,
            "approval_request_created",
            "ApprovalRequest de shell governado criado pelo chat.",
            {
                "source_channel": "chat",
                "session_id": session_id,
                "operation_id": decision.operation_id,
                "preview_id": preview.preview_id,
                "approval_id": approval.approval_id,
                "action_type": action,
            },
        )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            preview_id=preview.preview_id,
            approval_id=approval.approval_id,
            status="pending_approval",
            message=(
                "O comando foi reconhecido como shell governado e precisa de aprovacao antes de qualquer execucao. "
                "Nada foi executado. Revise o approval no Pipeline ou responda no chat com o approval_id."
            ),
            intent={
                "intent_type": "governed_shell_request",
                "requires_task": True,
                "requires_workspace": bool(workspace_ref),
                "requested_operation": action,
            },
            policy={
                "status": "needs_approval",
                "approval_required_for": [action],
                "safe_to_preview": True,
                "safe_to_execute": False,
                "workspace_ref": workspace_ref,
            },
            operation_id=decision.operation_id,
            operation_type="governed_shell_request",
            message_type="task_status_update",
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            grounding_missing_reason="approval_required_before_shell_execution",
            evidence_refs=[
                {"type": "task_preview", "ref_id": preview.preview_id, "human_label": "Preview de shell governado"},
                {"type": "approval_request", "ref_id": approval.approval_id, "human_label": "Approval de shell governado"},
            ],
            next_actions=[
                ChatNextAction(type="review_approval", label="Revisar aprovacao", target_id=approval.approval_id),
                ChatNextAction(type="reject", label="Negar acao governada", target_id=approval.approval_id),
            ],
            warnings=list(dict.fromkeys([*preview.warnings, "shell_requires_approval", "no_shell_executed"])),
            contract_preview={
                "draft": draft.model_dump(),
                "preview": preview.model_dump(),
                "approval": approval.model_dump(),
                "operation_contract": operation_contract.model_dump(),
            },
        )

    def _role_model_run_guidance_response(self, message: str, session_id: str | None) -> ChatResponse:
        target_role = self._extract_requested_role_id(message)
        target = target_role or "{role_id}"
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message=(
                f"Posso orientar a execucao controlada do role-model para {target}. "
                "Conversas e tasks usam bindings reais governados quando a policy permite, mas uma chamada direta a um role-model especifico continua exigindo preview/run ou contrato operacional rastreavel. "
                f"Use /api/v1/role-models/{target}/preview para validar gate/contrato e /api/v1/role-models/{target}/run para a execucao explicita."
            ),
            next_actions=[
                ChatNextAction(type="preview_role_model_run", label="Preview role-model", target_id=target_role),
                ChatNextAction(type="run_role_model_endpoint", label="Rodar via endpoint explicito", target_id=target_role),
            ],
            warnings=["direct_role_model_execution_requires_contract", "governed_auto_inference_enabled", "no_tool_calling_from_model"],
            model_used=None,
            real_inference=False,
        )

    def _extract_requested_role_id(self, message: str) -> str | None:
        lowered = message.lower()
        status = RoleModelStatusService().status()
        roles = status.get("roles", []) if isinstance(status.get("roles", []), list) else []
        for item in roles:
            if isinstance(item, dict):
                role_id = str(item.get("role_id", ""))
                if role_id and role_id.lower() in lowered:
                    return role_id
        return None

    def _requests_patch_apply(self, message: str) -> bool:
        lowered = message.lower()
        non_execution_terms = {
            "sem aplicar",
            "nao aplicar",
            "não aplicar",
            "nao aplique",
            "não aplique",
            "without apply",
            "preview",
            "proposta",
            "proponha",
            "planeje",
            "plano de correcao",
            "plano de correção",
            "correction plan",
            "validation plan",
            "rollback plan",
        }
        if any(term in lowered for term in non_execution_terms):
            return False
        return "patch" in lowered and any(term in lowered for term in {"aplique", "aplicar", "apply", "corrija agora"})

    def _requests_patch_quality(self, message: str) -> bool:
        lowered = message.lower()
        validation_terms = {"quality gate", "quality", "valide", "validar", "validacao", "validação", "seguro", "safety"}
        patch_terms = {"patch", "diff", "patchplan", "patch plan"}
        return any(term in lowered for term in patch_terms) and any(term in lowered for term in validation_terms)

    def _requests_patch_apply_status(self, message: str) -> bool:
        lowered = message.lower()
        return "patch" in lowered and any(term in lowered for term in {"foi aplicado", "status do apply", "status do patch", "aplicado?"})

    def _requests_patch_rollback(self, message: str) -> bool:
        lowered = message.lower()
        if "patch" not in lowered:
            return False
        planning_terms = {
            "rollback plan",
            "plano de rollback",
            "rollback notes",
            "rollback note",
            "notas de rollback",
            "resumo de rollback",
            "documente rollback",
            "documentar rollback",
        }
        if any(term in lowered for term in planning_terms):
            return False
        execution_terms = {
            "execute rollback",
            "executar rollback",
            "faça rollback",
            "faca rollback",
            "aplique rollback",
            "aplicar rollback",
            "restaure",
            "restaurar",
            "reverter",
            "reverta",
        }
        return any(term in lowered for term in execution_terms)

    def _requests_patch_plan(self, message: str) -> bool:
        lowered = message.lower()
        return ("patch" in lowered or "diff" in lowered) and any(term in lowered for term in {"proponha", "proposta", "preview", "sem aplicar", "planeje"})

    def _artifact_preview_from_chat(self, request: ChatRequest, session_id: str | None) -> ChatResponse | None:
        workspace = request.context.active_workspace if request.context else None
        target_path = self._extract_artifact_target_path(request.message)
        if not workspace:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Posso preparar um preview de artefato, mas preciso de um workspace ativo. Nenhum arquivo foi gravado.",
                next_actions=[ChatNextAction(type="provide_workspace", label="Informar workspace")],
                warnings=["workspace_required_for_artifact_preview", "chat_does_not_write_files"],
            )
        if not target_path:
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Posso preparar um preview de artefato, mas preciso de um target path permitido como reports/analise.md. Nenhum arquivo foi gravado.",
                next_actions=[ChatNextAction(type="revise_target_path", label="Informar target path")],
                warnings=["target_path_required_for_artifact_preview", "chat_does_not_write_files"],
            )
        from aipinho.schemas.artifacts.artifact_preview import ArtifactPreviewRequest
        from aipinho.schemas.artifacts.artifact_source import ArtifactSource
        from aipinho.services.artifacts.artifact_writer_preview_service import ArtifactWriterPreviewService
        source = ArtifactSource(source_type="user_provided_content", format="markdown", content=request.message, metadata={"created_from_chat": True})
        preview = ArtifactWriterPreviewService().create_preview(ArtifactPreviewRequest(workspace=workspace, target_path=target_path, source=source, artifact_type="report", title="Chat artifact preview"))
        if preview.status == "blocked":
            return ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="blocked",
                message=f"Preview de artefato bloqueado para {target_path}. Motivos: {', '.join(preview.blocked_reasons) or 'policy'}. Nenhum arquivo foi gravado.",
                next_actions=[ChatNextAction(type="revise_target_path", label="Revisar caminho do artefato", target_id=preview.preview_id)],
                warnings=list(dict.fromkeys([*preview.warnings, "artifact_preview_blocked", "chat_does_not_write_files"])),
            )
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message=f"Criei um preview de artefato para {target_path}. Ele requer aprovacao para escrita futura. Nenhum arquivo foi gravado.",
            next_actions=[
                ChatNextAction(type="view_artifact_preview", label="Ver preview de artefato", target_id=preview.preview_id),
                ChatNextAction(type="request_artifact_approval", label="Solicitar aprovacao", target_id=preview.preview_id),
                ChatNextAction(type="create_artifact_write_run", label="Criar write run apos approval", target_id=preview.preview_id),
            ],
            warnings=list(dict.fromkeys([*preview.warnings, "artifact_write_requires_approval_and_execute_endpoint", "chat_does_not_write_files"])),
        )

    def _extract_artifact_target_path(self, message: str) -> str | None:
        import re
        match = re.search(r"(?i)(reports|artifacts|exports|docs/generated|src|tests|config|scripts)[\\/][^\s\"']+\.(md|txt|json|ya?ml|csv|html|py|js|ts|tsx|jsx|kt|ps1|bat|sh)", message)
        return match.group(0).strip().strip(".,;") if match else None


    def _apply_session_context(self, intent_map: Any, session_state: Any) -> Any:
        if (
            getattr(intent_map, "intent_type", "unknown") == "conversation"
            and getattr(intent_map, "object", "unknown") in {"architecture", "project"}
            and getattr(intent_map, "operation", "unknown") in {"explain", "analyze"}
            and getattr(session_state, "active_workspace_candidate", None)
        ):
            intent_map.intent_type = "readonly_analysis"
            intent_map.task_type = "readonly_analysis"
            intent_map.requires_task = True
            intent_map.requires_workspace = True
            intent_map.requested_actions = ["read_files"]
            intent_map.warnings = list(dict.fromkeys([*intent_map.warnings, "workspace_candidate_requires_confirmation"]))
        return intent_map

    def _include_trace(self, request: ChatRequest) -> bool:
        return bool(request.include_trace or request.mode in {"preview", "debug"} or self.response_policy.include_trace_by_default())

    def _chat_status(self, intent_map: Any, policy_decision: PolicyDecision, request: ChatRequest) -> str:
        if intent_map.workspace.protected or policy_decision.status == "denied":
            return "blocked"
        if intent_map.ambiguity.requires_clarification or policy_decision.status == "needs_clarification":
            return "needs_clarification"
        if intent_map.intent_type in self.DIRECT_INTENTS and request.mode == "normal":
            return "ok"
        if policy_decision.status == "needs_approval" or intent_map.requires_task or request.mode == "preview":
            return "preview"
        return "ok"

    def _intent_summary(self, intent_map: Any, *, detailed: bool) -> dict[str, Any]:
        summary = {
            "intent_id": intent_map.intent_id,
            "intent_type": intent_map.intent_type,
            "task_type": intent_map.task_type,
            "requires_task": intent_map.requires_task,
            "requires_workspace": intent_map.requires_workspace,
            "requires_approval": intent_map.requires_approval,
            "risk": intent_map.risk.level,
            "requires_clarification": intent_map.ambiguity.requires_clarification,
            "workspace": {"declared": intent_map.workspace.declared, "path": intent_map.workspace.path, "protected": intent_map.workspace.protected},
            "output_channel": intent_map.output_intent.channel,
        }
        if detailed:
            summary["requested_actions"] = list(intent_map.requested_actions)
            summary["segments"] = [_to_dict(segment) for segment in intent_map.segments]
            summary["evidence"] = [_to_dict(item) for item in intent_map.evidence]
        return summary

    def _policy_summary(self, policy_decision: PolicyDecision) -> dict[str, Any]:
        return {
            "status": policy_decision.status,
            "contract_type": policy_decision.contract_type,
            "allowed_actions": policy_decision.allowed_actions,
            "denied_actions": policy_decision.denied_actions,
            "approval_required_for": policy_decision.approval_required_for,
            "safe_to_preview": policy_decision.safe_to_preview,
            "safe_to_execute": policy_decision.safe_to_execute,
        }

    def _suggested_actions(self, status: str, policy_decision: PolicyDecision) -> list[str]:
        if status == "needs_clarification":
            return ["clarify_request"]
        if status == "preview":
            actions = ["review_contract_preview"]
            if policy_decision.approval_required_for:
                actions.append("request_approval_before_execution")
            return actions
        return []

    def _next_actions(self, status: str, draft: Any | None, preview: Any | None = None) -> list[ChatNextAction]:
        if status == "needs_clarification":
            target_id = draft.draft_id if draft is not None else None
            actions = [ChatNextAction(type="clarify", label="Responder esclarecimento", target_id=target_id)]
            if draft is not None and draft.workspace.status in {"missing", "candidate"}:
                actions.append(ChatNextAction(type="provide_workspace", label="Informar ou confirmar workspace", target_id=draft.draft_id))
            return actions
        if status == "blocked":
            return [ChatNextAction(type="cancel", label="Cancelar pedido", target_id=draft.draft_id if draft is not None else None)]
        if draft is not None:
            target = preview.preview_id if preview is not None else draft.draft_id
            actions = [ChatNextAction(type="approve_preview", label="Revisar preview do rascunho", target_id=target)]
            if preview is not None and self._preview_is_readonly_executable(preview):
                actions.insert(0, ChatNextAction(type="execute_readonly", label="Executar leitura controlada", target_id=preview.preview_id))
                actions.insert(0, ChatNextAction(type="build_file_context", label="Montar contexto de arquivos", target_id=preview.preview_id))
                actions.insert(0, ChatNextAction(type="run_readonly_analysis", label="Analisar projeto sem alterar arquivos", target_id=preview.preview_id))
                actions.insert(0, ChatNextAction(type="run_project_report", label="Gerar report deterministico no chat", target_id=preview.preview_id))
                actions.insert(0, ChatNextAction(type="create_task_run", label="Criar TaskRun read-only supervisionada", target_id=preview.preview_id))
            elif preview is not None and preview.status in {"preview_ready", "approval_required"}:
                actions.insert(0, ChatNextAction(type="dry_run_preview", label="Simular ferramentas do preview", target_id=preview.preview_id))
            if preview is not None and preview.status == "approval_required":
                if "write_files" in set(getattr(preview, "requested_actions", []) or []) or "write_files" in set(getattr(preview, "approval_required_for", []) or []):
                    actions.append(ChatNextAction(type="preview_report_artifact", label="Gerar preview de artefato sem escrever", target_id=preview.preview_id))
                actions.append(ChatNextAction(type="create_approval", label="Criar pedido de aprovacao", target_id=preview.preview_id))
            if draft.workspace.status in {"missing", "candidate"}:
                actions.append(ChatNextAction(type="provide_workspace", label="Informar ou confirmar workspace", target_id=draft.draft_id))
            return actions
        return []

    def _runtime_next_actions(self, task_run: Any) -> list[ChatNextAction]:
        actions = [ChatNextAction(type="view_task_run", label="Acompanhar task", target_id=task_run.run_id)]
        if task_run.status in {"created", "queued", "running", "waiting_input"}:
            actions.append(ChatNextAction(type="cancel_task_run", label="Cancelar task", target_id=task_run.run_id))
        if task_run.status == "waiting_input" and task_run.approval_id:
            actions.insert(0, ChatNextAction(type="approve", label="Aprovar acao governada", target_id=task_run.approval_id))
            actions.insert(1, ChatNextAction(type="reject", label="Negar acao governada", target_id=task_run.approval_id))
        return actions

    def _materialize_task_run(self, preview: Any | None, intent_map: Any, request: ChatRequest) -> tuple[Any | None, str | None]:
        if (
            request.mode != "normal"
            or preview is None
            or preview.status not in {"preview_ready", "approval_required"}
            or not bool(getattr(intent_map, "requires_task", False))
        ):
            return None, None
        task_run = self.task_runtime_service.create_from_preview(
            preview.preview_id,
            {
                "start_immediately": preview.status == "preview_ready",
                "include_trace": self._include_trace(request),
            },
        )
        if task_run.status == "waiting_input":
            return task_run, "pending_approval"
        if task_run.status == "blocked":
            return task_run, "blocked"
        return task_run, "ready"

    def _preview_is_readonly_executable(self, preview: Any) -> bool:
        allowed = set(self.read_only_execution_policy.get("read_only_execution", {}).get("allowed_actions", []) or [])
        requested = set(getattr(preview, "requested_actions", []) or [])
        return getattr(preview, "status", None) == "preview_ready" and bool(requested) and requested.issubset(allowed)
    def _trace_items(self, analysis_trace: list[Any], policy_decision: PolicyDecision, *, include: bool) -> list[ChatTraceItem]:
        if not include:
            return []
        raw_items = [*_to_list(analysis_trace), *_to_list(policy_decision.trace)]
        return [
            ChatTraceItem(
                stage=str(item.get("stage", "unknown")),
                status=str(item.get("decision", item.get("status", "ok"))),
                reason=str(item.get("reason", "")),
                source=item.get("source"),
                data={k: v for k, v in item.items() if k not in {"stage", "decision", "status", "reason", "source"}},
            )
            for item in self.trace_service.compact(raw_items)
        ]

    def status(self) -> dict[str, object]:
        dependencies = {
            "prompt_intelligence": self.prompt_intelligence.status(),
            "effective_policy_decision": self.policy_decisions.status(),
            "speaker": self.speaker.status(),
            "interpreter": self.interpreter.status(),
            "response_policy": self.response_policy.status(),
            "session": self.session_service.status(),
            "task_draft": self.task_draft_service.status(),
            "preview": self.task_preview_service.status(),
            "approval": self.approval_service.status(),
            "artifacts": __import__("aipinho.services.artifacts.artifact_writer_preview_service", fromlist=["ArtifactWriterPreviewService"]).ArtifactWriterPreviewService().status().model_dump(),
            "artifact_write": __import__("aipinho.services.artifacts.artifact_write_execution_service", fromlist=["ArtifactWriteExecutionService"]).ArtifactWriteExecutionService().status().model_dump(),
            "patch_planning": __import__("aipinho.services.patching.patch_planning_service", fromlist=["PatchPlanningService"]).PatchPlanningService().status().model_dump(),
            "patch_quality": __import__("aipinho.services.patching.quality.patch_quality_gate_service", fromlist=["PatchQualityGateService"]).PatchQualityGateService().status(),
            "patch_apply": __import__("aipinho.services.patching.apply.patch_apply_service", fromlist=["PatchApplyService"]).PatchApplyService().status().model_dump(),
            "read_only_execution": ReadOnlyExecutionService().status(),
            "project_analysis": ProjectAnalysisService().status(),
            "project_report": ProjectReportService().status(),
            "prompt_assembly": self.prompt_assembly_service.status(),
            "model_invocation": self.model_invocation_service.status(),
            "model_status": ModelStatusService().status(),
            "llama_cpp": LlamaCppStatusService().status().model_dump(),
            "manual_inference": ManualInferenceStatusService().status().model_dump(),
            "role_pipeline": RolePipelineService().status(),
            "role_model_status": RoleModelStatusService().status(),
            "task_runtime": self.task_runtime_service.status().model_dump(),
            "validation_gate": __import__("aipinho.services.validation.validation_gate_service", fromlist=["ValidationGateService"]).ValidationGateService().status(),
            "chat_model_policy": ChatModelPolicyService().status(),
            "chat_manual_inference": ChatManualInferenceService().status(),
            "memory_candidate": __import__("aipinho.services.memory.memory_candidate_service", fromlist=["MemoryCandidateService"]).MemoryCandidateService().status(),
            "curated_memory": __import__("aipinho.services.memory.curated_memory_service", fromlist=["CuratedMemoryService"]).CuratedMemoryService().status(),
            "memory_read_policy": __import__("aipinho.services.memory.memory_read_policy_service", fromlist=["MemoryReadPolicyService"]).MemoryReadPolicyService().status(),
            "retrieval": __import__("aipinho.services.rag.retrieval_service", fromlist=["RetrievalService"]).RetrievalService().status(),
            "rag_memory_integration": __import__("aipinho.services.rag.integration.rag_memory_status_service", fromlist=["RAGMemoryStatusService"]).RAGMemoryStatusService().status(),
            "vector_rag": VectorRAGStatusService().status(),
        }
        healthy_statuses = {"ok", "disabled", "available", "healthy"}
        nonblocking_dependencies = {"model_status", "vector_rag"}
        overall = "ok" if all(
            item.get("status") in healthy_statuses or (name in nonblocking_dependencies and item.get("status") == "degraded")
            for name, item in dependencies.items()
        ) else "degraded"
        return {"status": overall, "service": "chat", "execution_enabled": False, "dependencies": dependencies}



















