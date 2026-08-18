from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from uuid import uuid4

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.chat.chat_response import ChatArtifactLink, ChatNextAction, ChatResponse
from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.schemas.chat.manual_chat_inference_response import ManualChatInferenceResponse
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.chat.chat_attachment_context_service import ChatAttachmentContextService
from aipinho.services.chat.chat_manual_inference_service import ChatManualInferenceService
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.chat.chat_artifact_fulfillment_service import ChatArtifactFulfillmentService
from aipinho.services.chat.artifact_request_preview_service import ArtifactRequestPreviewService
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision, ChatOperationRouterService
from aipinho.services.chat.chat_persistence_gate_service import ChatPersistenceGateService
from aipinho.services.chat.chat_permission_grant_service import ChatPermissionGrantService
from aipinho.services.chat.governed_configuration_change_chat_service import GovernedConfigurationChangeChatService
from aipinho.services.chat.governed_write_chat_service import GovernedWriteChatService
from aipinho.services.chat.followup_result_review_service import FollowupResultReviewService
from aipinho.services.chat.permission_status_response_service import PermissionStatusResponseService
from aipinho.services.chat.workspace_metadata_query_service import WorkspaceMetadataQueryService
from aipinho.services.chat.blocked_policy_response_service import BlockedPolicyResponseService
from aipinho.services.chat.chat_result_index_service import ChatResultIndexService
from aipinho.services.chat.chat_router_service import ChatRouterService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.readonly_project_analysis_preview_service import ReadonlyProjectAnalysisPreviewService
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.projects.project_rebuild_preview_service import ProjectRebuildPreviewService
from aipinho.services.chat.session_diagnostic_service import SessionDiagnosticService
from aipinho.services.chat.session_execution_report_service import SessionExecutionReportService
from aipinho.schemas.artifacts.workspace_evidence_bundle import WorkspaceEvidenceBundleRequest
from aipinho.services.artifacts.workspace_evidence_bundle_service import WorkspaceEvidenceBundleService
from aipinho.schemas.artifacts.workspace_static_reachability_report import WorkspaceStaticReachabilityReportRequest
from aipinho.services.artifacts.workspace_static_reachability_report_service import WorkspaceStaticReachabilityReportService
from aipinho.schemas.artifacts.workspace_readonly_audit_report import WorkspaceReadonlyAuditReportRequest
from aipinho.services.artifacts.workspace_readonly_audit_report_service import WorkspaceReadonlyAuditReportService
from aipinho.schemas.projects.project_rebuild_preview import ProjectRebuildPreviewRequest

from aipinho.schemas.interaction.contracts import ChatMessageCreateRequest, ChatSessionCreateRequest, ChatSessionRenameRequest, FeedbackRequest
from aipinho.services.interaction.interaction_core import ChatMessageService, ChatSessionService, FeedbackService, ChatTimelineService, CopyActionService, SanitizedRawService, SpeakerMessageService
from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.runtime_state_hygiene_service import RuntimeStateHygieneService
from aipinho.services.roles.role_pipeline_service import RolePipelineService
from aipinho.services.session.session_store import utc_now

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatApprovalCommandRequest(AIpinhoModel):
    session_id: str
    text: str
    message_id: str | None = None
    source_channel: str = "api"


@router.get("/status")
def get_chat_status() -> dict[str, object]:
    runtime = TaskRuntimeService().status()
    roles = RolePipelineService().status()
    return {
        "status": "ok",
        "service": "chat",
        "lightweight": True,
        "backend_alive": True,
        "execution_enabled": bool(runtime.enabled),
        "execution_summary": {
            "mode": runtime.mode,
            "write_enabled": runtime.write_enabled,
            "patch_enabled": runtime.patch_enabled,
            "shell_enabled": runtime.shell_enabled,
            "allowed_actions": runtime.allowed_actions,
        },
        "role_pipeline": {
            "status": roles.get("status"),
            "silent_stub_fallback": roles.get("silent_stub_fallback"),
            "bindings": (roles.get("role_model_bindings") or {}).get("bindings") if isinstance(roles.get("role_model_bindings"), dict) else None,
        },
        "diagnostics_endpoint": "/api/v1/chat/diagnostics",
    }


@router.get("/diagnostics")
def get_chat_diagnostics() -> dict[str, object]:
    return ChatService().status()


@router.post("")
def post_chat(request: ChatRequest) -> ChatResponse:
    try:
        return ChatService().respond(request)
    except ValueError as exc:
        if str(exc) == "invalid_session_id":
            raise HTTPException(status_code=409, detail="invalid_session_id") from exc
        raise


@router.post("/preview")
def post_chat_preview(request: ChatRequest) -> ChatResponse:
    preview_request = ChatRouterService().force_preview(request)
    return ChatService().respond(preview_request)


@router.post("/approval-command")
def post_chat_approval_command(request: ChatApprovalCommandRequest) -> dict[str, object]:
    response = ChatApprovalCommandService().handle(
        request.session_id,
        request.text,
        source_channel=request.source_channel,
        message_id=request.message_id,
    )
    if response is None:
        return {
            "status": "not_found",
            "approval_id": None,
            "message": "Nenhum comando de approval reconhecido.",
        }
    status = str(response.status)
    reason_code = str(response.policy.get("reason_code") or "") if isinstance(response.policy, dict) else ""
    if status == "ok":
        api_status = "approved" if response.approval_id and "liberada" in response.message.casefold() else "ok"
    elif reason_code == "approval_ambiguous_decision":
        api_status = "ambiguous"
    elif reason_code == "approval_not_found":
        api_status = "not_found"
    elif reason_code == "approval_expired":
        api_status = "expired"
    else:
        api_status = status
    return {
        "status": api_status,
        "approval_id": response.approval_id,
        "message": response.message,
        "chat_response": response.model_dump(),
    }


@router.get("/model-status")
def get_chat_model_status() -> dict[str, object]:
    return ChatModelPolicyService().status()


@router.post("/manual-inference/preview")
def post_chat_manual_inference_preview(request: ManualChatInferenceRequest) -> ManualChatInferenceResponse:
    return ChatManualInferenceService().preview(request)


@router.post("/manual-inference")
def post_chat_manual_inference(request: ManualChatInferenceRequest) -> ManualChatInferenceResponse:
    return ChatManualInferenceService().run(request)


@router.post("/sessions")
def create_chat_session(request: ChatSessionCreateRequest) -> dict[str, object]:
    return {"status": "ok", "session": ChatSessionService().create(request).model_dump()}


@router.get("/sessions")
def list_chat_sessions(limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> dict[str, object]:
    sessions = sorted(ChatSessionService().list(), key=lambda session: session.updated_at, reverse=True)
    selected = sessions[offset: offset + limit]
    return {
        "status": "ok",
        "total": len(sessions),
        "limit": limit,
        "offset": offset,
        "sessions": [session.model_dump() for session in selected],
    }


@router.get("/sessions/{session_id}")
def get_chat_session(session_id: str) -> dict[str, object]:
    session = ChatSessionService().get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="chat_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


def _rename_chat_session_payload(session_id: str, request: ChatSessionRenameRequest) -> dict[str, object]:
    try:
        session = ChatSessionService().rename(session_id, request.title)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if session is None:
        raise HTTPException(status_code=404, detail="chat_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.patch("/sessions/{session_id}")
def rename_chat_session(session_id: str, request: ChatSessionRenameRequest) -> dict[str, object]:
    return _rename_chat_session_payload(session_id, request)


@router.post("/sessions/{session_id}/rename")
def rename_chat_session_post(session_id: str, request: ChatSessionRenameRequest) -> dict[str, object]:
    return _rename_chat_session_payload(session_id, request)


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: str) -> dict[str, object]:
    service = ChatSessionService()
    if service.get(session_id) is None:
        raise HTTPException(status_code=404, detail="chat_session_not_found")
    deleted_messages = ChatMessageService().delete_for_session(session_id)
    deleted = service.delete(session_id)
    return {"status": "ok", "deleted": deleted, "session_id": session_id, "deleted_messages": deleted_messages}


@router.post("/sessions/{session_id}/messages")
def create_chat_message(session_id: str, request: ChatMessageCreateRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "message": ChatMessageService().create(session_id, request).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="chat_session_not_found") from exc


@router.post("/sessions/{session_id}/send")
def send_chat_session_message(session_id: str, request: ChatMessageCreateRequest) -> dict[str, object]:
    if request.role != "user":
        raise HTTPException(status_code=409, detail="chat_send_accepts_user_messages_only")
    message_service = ChatMessageService()
    try:
        user_message = message_service.create(
            session_id,
            ChatMessageCreateRequest(
                role="user",
                content=request.content,
                task_id=None,
                metadata={**request.metadata, "source": "persistent_chat_send"},
            ),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="chat_session_not_found") from exc
    attachment_context = ChatAttachmentContextService().from_metadata(request.metadata)
    prompt_for_processing = _prompt_with_attachment_context(request.content, attachment_context.context_text)
    request_workspace = _request_workspace_context(request.metadata)
    session_workspace = request_workspace or _latest_persistent_workspace_context(session_id)
    approval_command_response = ChatApprovalCommandService().handle(
        session_id,
        request.content,
        source_channel=str(request.metadata.get("source_channel") or request.metadata.get("source") or "launcher_or_mobile_chat"),
        message_id=user_message.message_id,
    )
    if approval_command_response is not None:
        assistant_message = message_service.create(
            session_id,
            ChatMessageCreateRequest(
                role="assistant",
                content=approval_command_response.message,
                task_id=approval_command_response.task_id,
                metadata={
                    "chat_response": approval_command_response.model_dump(),
                    "source": "approval_command",
                },
            ),
        )
        return {
            "status": "ok",
            "user_message": user_message.model_dump(),
            "assistant_message": assistant_message.model_dump(),
            "chat_response": approval_command_response.model_dump(),
            "timeline": ChatTimelineService().timeline(session_id).model_dump(),
        }
    grant_response = ChatPermissionGrantService().handle(
        session_id=session_id,
        text=request.content,
        source_channel=str(request.metadata.get("source_channel") or request.metadata.get("source") or "launcher_or_mobile_chat"),
        active_workspace=session_workspace,
    )
    if grant_response is not None:
        assistant_message = message_service.create(
            session_id,
            ChatMessageCreateRequest(
                role="assistant",
                content=grant_response.message,
                task_id=grant_response.task_id,
                metadata={
                    "chat_response": grant_response.model_dump(),
                    "source": "session_permission_grant",
                },
            ),
        )
        return {
            "status": "ok",
            "user_message": user_message.model_dump(),
            "assistant_message": assistant_message.model_dump(),
            "chat_response": grant_response.model_dump(),
            "timeline": ChatTimelineService().timeline(session_id).model_dump(),
        }
    decision = ChatOperationRouterService().route(request.content, workspace_hint=session_workspace)
    session_workspace = decision.workspace or session_workspace
    queue_health = RuntimeStateHygieneService().queue_health(max_age_hours=1)
    if queue_health.get("dispatcher_status") == "saturated":
        chat_response = ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            status="degraded",
            message="Recebi sua mensagem, mas a fila de execucao esta aguardando um slot livre. Vou manter isso visivel em vez de deixar o chat silencioso.",
            warnings=[str(queue_health.get("reason_code") or "dispatcher_saturated")],
            policy={"queue_health": queue_health},
        )
    else:
        try:
            chat_response = _persistent_chat_response(
                session_id,
                prompt_for_processing,
                decision,
                attachment_context=attachment_context,
                request_metadata=request.metadata,
                session_workspace=session_workspace,
            )
        except Exception as exc:
            reason_code = "dispatch_response_failed"
            chat_response = ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=session_id,
                status="error",
                message="Recebi sua mensagem, mas a resposta falhou de forma controlada. O backend continua vivo; abra Detalhes/Debugger para ver o motivo tecnico sanitizado.",
                warnings=[reason_code, exc.__class__.__name__],
                policy={"reason_code": reason_code, "error_type": exc.__class__.__name__},
            )
    gate = ChatPersistenceGateService()
    chat_response = gate.decorate(chat_response, decision)
    if chat_response.session_id != session_id:
        chat_response = chat_response.model_copy(update={"session_id": session_id})
    if chat_response.is_final_answer and chat_response.grounded and chat_response.result_ref_id is None:
        chat_response = chat_response.model_copy(update={"result_ref_id": f"result_{uuid4().hex}"})
    assistant_metadata = gate.metadata(chat_response, decision)
    assistant_message = message_service.create(
        session_id,
        ChatMessageCreateRequest(
            role="assistant",
            content=chat_response.message,
            task_id=gate.assistant_task_id(chat_response),
            metadata=assistant_metadata,
        ),
    )
    result_ref_id = ChatResultIndexService().add_final_answer(session_id, chat_response, assistant_message.message_id)
    if result_ref_id and chat_response.result_ref_id != result_ref_id:
        chat_response = chat_response.model_copy(update={"result_ref_id": result_ref_id})
    return {
        "status": "ok",
        "user_message": user_message.model_dump(),
        "assistant_message": assistant_message.model_dump(),
        "chat_response": chat_response.model_dump(),
        "timeline": ChatTimelineService().timeline(session_id).model_dump(),
    }


def _persistent_chat_response(
    session_id: str,
    prompt: str,
    decision: ChatOperationDecision,
    *,
    attachment_context=None,
    request_metadata: dict[str, object] | None = None,
    session_workspace: str | None = None,
) -> ChatResponse:
    active_workspace = decision.workspace or session_workspace
    context = ChatContext(surface="mobile", active_workspace=active_workspace)
    if decision.operation_type == "session_execution_report":
        return SessionExecutionReportService().report(session_id, decision)
    if decision.operation_type == "session_diagnostic":
        return SessionDiagnosticService().diagnose(session_id, decision)
    if decision.operation_type == "permission_status":
        return PermissionStatusResponseService().respond(session_id=session_id, operation_id=decision.operation_id)
    if decision.operation_type == "workspace_metadata_query":
        return WorkspaceMetadataQueryService().respond(session_id=session_id, decision=decision)
    if decision.operation_type == "governed_configuration_change":
        return GovernedConfigurationChangeChatService().preview(
            session_id=session_id,
            decision=decision,
            prompt=prompt,
        )
    if decision.operation_type in {"public_fact_query", "sandbox_batch_artifact_request", "filesystem_write_file", "filesystem_create_directory", "filesystem_read_file", "filesystem_append_file", "sandbox_capability_test", "android_apk_build", "artifact_build_request"}:
        return ChatService().respond(ChatRequest(message=prompt, session_id=session_id, mode="normal", include_trace=False, context=context))
    metadata_with_context = {**(request_metadata or {})}
    if active_workspace and "workspace_context" not in metadata_with_context:
        metadata_with_context["_session_workspace_context"] = active_workspace
    if str(decision.metadata.get("router_operation_type") or "") == "workspace_evidence_bundle":
        return _workspace_evidence_bundle_response(
            session_id=session_id,
            prompt=prompt,
            decision=decision,
            request_metadata=metadata_with_context,
            workspace_ref=active_workspace,
        )
    if str(decision.metadata.get("router_operation_type") or "") == "workspace_static_reachability_report":
        return _workspace_static_reachability_response(
            session_id=session_id,
            prompt=prompt,
            decision=decision,
            request_metadata=metadata_with_context,
            workspace_ref=active_workspace,
        )
    if str(decision.metadata.get("router_operation_type") or "") == "workspace_readonly_audit_report":
        return _workspace_readonly_audit_response(
            session_id=session_id,
            prompt=prompt,
            decision=decision,
            request_metadata=metadata_with_context,
            workspace_ref=active_workspace,
        )
    local_create_response = _try_persistent_chat_local_create_file(session_id, prompt, decision, metadata_with_context)
    if local_create_response is not None:
        return _decorate_attachment_response(local_create_response, attachment_context)
    if decision.operation_type == "workspace_artifact_write_request":
        workspace_decision = WorkspaceRoleContractService().load().resolve(decision.workspace, required=True)
        contract = workspace_decision.contract
        allowed = False
        reason = workspace_decision.reason
        if workspace_decision.status == "allowed" and contract is not None:
            allowed, reason = WorkspaceRoleContractService().load().operation_allowed(contract, "create_file")
        if not allowed:
            return BlockedPolicyResponseService().build(
                session_id=session_id,
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                policy_name="workspace_role_contract",
                block_reason_code=reason,
                human_reason="O workspace selecionado nao permite escrita para esta operacao.",
                safe_alternatives=["Gere o resultado no artifact store ou escolha um target_mutable registrado."],
                requested_capability="write_workspace",
                requested_action="create_file",
                workspace_id=contract.workspace_id if contract else None,
                workspace_role=contract.role if contract else None,
                evidence_refs=[
                    {
                        "type": "workspace_policy",
                        "ref_id": contract.workspace_id if contract else "workspace_resolution",
                        "human_label": "Workspace role contract",
                    }
                ],
            )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="preview",
            message=(
                "A escrita no workspace pode prosseguir somente pelo fluxo governado. "
                "Primeiro crie o preview; depois sao exigidos approval e validacao antes de qualquer gravacao."
            ),
            intent={
                "intent_type": decision.operation_type,
                "requires_task": True,
                "requires_workspace": True,
                "output_target": "workspace",
            },
            policy={
                "workspace_write": True,
                "approval_required_for": ["create_file"],
                "required_preconditions": ["write_envelope", "preview", "approval", "validation"],
                "workspace_id": contract.workspace_id,
                "workspace_role": contract.role,
            },
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            message_type="artifact_preview",
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            evidence_refs=[
                {
                    "type": "workspace_policy",
                    "ref_id": contract.workspace_id,
                    "human_label": "Workspace role contract",
                }
            ],
        )
    if decision.operation_type == "followup_result_recall":
        recall_kind = str(decision.metadata.get("recall_kind") or "answer")
        result = ChatResultIndexService().latest_final_answer(session_id, result_kind=recall_kind)
        if result is None:
            missing_label = "resumo real" if recall_kind == "summary" else "resultado final fundamentado"
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="degraded",
                message=f"Ainda nao tenho um {missing_label} nesta conversa para repetir. Posso continuar quando houver uma resposta final ou report real no historico.",
                intent={"intent_type": "followup_result_recall", "requires_task": False, "requires_workspace": False},
                policy={"approval_required_for": []},
                warnings=["grounded_result_not_found"],
                message_type="assistant_degraded_answer",
                operation_type=decision.operation_type,
                operation_id=decision.operation_id,
                is_final_answer=False,
                grounded=False,
                grounding_required=True,
                grounding_missing_reason="no_indexed_final_result",
            )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=str(result.get("summary") or "Resultado final registrado sem resumo disponivel."),
            intent={"intent_type": "followup_result_recall", "requires_task": False, "requires_workspace": False},
            policy={"approval_required_for": []},
            message_type="assistant_final_answer",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            result_ref_id=str(result.get("result_ref_id") or ""),
            evidence_refs=[{"type": "chat_result", "ref_id": str(result.get("result_ref_id") or "")}],
            is_final_answer=True,
            grounded=True,
        )
    if decision.operation_type == "followup_result_review":
        return FollowupResultReviewService().review(session_id, decision)
    if decision.operation_type == "patch_preview" and str(decision.metadata.get("router_operation_type") or "") == "governed_change_plan":
        response = ChatService().respond(ChatRequest(message=prompt, session_id=session_id, mode="preview", include_trace=True, context=context))
        return response.model_copy(
            update={
                "operation_id": decision.operation_id,
                "operation_type": decision.operation_type,
                "message_type": "task_preview",
                "is_final_answer": False,
                "grounding_required": True,
                "grounding_missing_reason": "governed_change_plan_not_applied",
            }
        )
    router_operation = str(decision.metadata.get("router_operation_type") or "")
    if decision.operation_type == "governed_project_rebuild" or router_operation == "governed_project_rebuild":
        if isinstance(decision.metadata.get("phase_resume"), dict):
            return _phase_resume_implementation_response(
                session_id=session_id,
                prompt=prompt,
                decision=decision,
                workspace_ref=decision.workspace or active_workspace,
            )
        result = ProjectRebuildPreviewService().create_preview(
            ProjectRebuildPreviewRequest(
                session_id=session_id,
                prompt=prompt,
                target_workspace=decision.workspace or "",
                operation_id=decision.operation_id,
            )
        )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            preview_id=result.plan_id,
            task_preview_id=result.plan_id,
            approval_id=result.approval_id,
            status="pending_approval" if result.status == "pending_approval" else ("preview" if result.status == "preview" else "blocked"),
            message=result.message,
            intent={
                "intent_type": "governed_project_rebuild",
                "requires_task": True,
                "requires_workspace": True,
                "source_workspace": result.source_workspace,
                "target_workspace": result.target_workspace,
                "files_selected": len(result.files),
                "files_omitted": len(result.omitted_files),
            },
            policy={
                "workspace_write": True,
                "approval_required_for": ["patch_apply"] if result.approval_id else [],
                "required_preconditions": ["source_read", "patch_preview", "quality_gate", "approval", "post_apply_validation"],
                "quality_id": result.quality_id,
                "source_run_id": result.source_run_id,
                "blocked_reasons": result.blocked_reasons,
            },
            contract_preview={
                "operation_type": "governed_project_rebuild",
                "plan_id": result.plan_id,
                "quality_id": result.quality_id,
                "approval_id": result.approval_id,
                "source_workspace": result.source_workspace,
                "target_workspace": result.target_workspace,
                "files": [item.model_dump() for item in result.files],
                "omitted_files": [item.model_dump() for item in result.omitted_files],
            },
            next_actions=[
                ChatNextAction(type="view_patch_plan", label="Ver preview do patch", target_id=result.plan_id),
                *(
                    [ChatNextAction(type="approve_patch_apply", label="Aprovar aplicacao do patch", target_id=result.approval_id)]
                    if result.approval_id
                    else []
                ),
            ],
            warnings=result.warnings,
            operation_id=decision.operation_id,
            operation_type=router_operation or decision.operation_type,
            message_type="task_preview",
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
            grounding_missing_reason="operation_preview_not_final_result",
            evidence_refs=[
                {"type": "task_run_result", "ref_id": result.source_run_id or "", "human_label": "Ultima analise read-only"},
                {"type": "patch_plan", "ref_id": result.plan_id or "", "human_label": "Preview de rebuild governado"},
            ],
        )
    if decision.operation_type == "readonly_analysis_with_artifact_output":
        response = ChatArtifactFulfillmentService().fulfill_readonly_analysis(session_id=session_id, prompt=prompt, decision=decision)
        return _decorate_attachment_response(response, attachment_context)
    if decision.operation_type == "readonly_project_analysis":
        base = ChatService().respond(ChatRequest(message=prompt, session_id=session_id, mode="preview", include_trace=False, context=context))
        return _decorate_attachment_response(ReadonlyProjectAnalysisPreviewService().from_response(base, decision), attachment_context)
    if decision.operation_type == "operational_task_request":
        response = ChatService().respond(ChatRequest(message=prompt, session_id=session_id, mode="preview", include_trace=True, context=context))
        return _decorate_attachment_response(
            response.model_copy(
                update={
                    "operation_id": decision.operation_id,
                    "operation_type": decision.operation_type,
                    "message_type": "task_preview",
                    "is_final_answer": False,
                    "grounding_required": True,
                    "grounding_missing_reason": "task_preview_not_execution_result",
                }
            ),
            attachment_context,
        )
    if decision.operation_type == "filesystem_archive_request":
        return _decorate_attachment_response(ChatArtifactFulfillmentService().fulfill_filesystem_archive(session_id=session_id, decision=decision), attachment_context)
    if decision.operation_type == "artifact_request":
        factual_response = None
        if decision.primary_prompt and decision.primary_prompt.strip() and decision.primary_prompt.strip() != prompt.strip():
            factual_prompt = _prompt_with_attachment_context(decision.primary_prompt, getattr(attachment_context, "context_text", ""))
            factual_response = ChatService().respond(ChatRequest(message=factual_prompt, session_id=session_id, mode="normal", include_trace=False, context=ChatContext(surface="mobile")))
        if factual_response is not None and factual_response.status == "ok" and factual_response.message.strip():
            return _decorate_attachment_response(ChatArtifactFulfillmentService().fulfill_response_artifact(session_id=session_id, decision=decision, factual_response=factual_response), attachment_context)
        return _decorate_attachment_response(ArtifactRequestPreviewService().offer(decision, factual_response), attachment_context)
    return _decorate_attachment_response(ChatService().respond(ChatRequest(message=prompt, session_id=session_id, mode="normal", include_trace=False, context=context)), attachment_context)


def _phase_resume_implementation_response(
    *,
    session_id: str,
    prompt: str,
    decision: ChatOperationDecision,
    workspace_ref: str | None,
) -> ChatResponse:
    now = utc_now()
    draft_store = TaskDraftStore()
    preview_service = TaskPreviewService(draft_store=draft_store)
    approval_service = ApprovalService(preview_service=preview_service, draft_store=draft_store)
    phase_resume = decision.metadata.get("phase_resume") if isinstance(decision.metadata.get("phase_resume"), dict) else {}
    evidence_report_path = str(phase_resume.get("evidence_report_path") or decision.metadata.get("evidence_report_path") or "")
    next_phase = str(phase_resume.get("next_phase") or "implementation_plan")
    action = "write_files"
    implementation_plan = {
        "plan_kind": "implementation_plan_only",
        "target_workspace": workspace_ref,
        "evidence_report_path": evidence_report_path,
        "next_phase": next_phase,
        "requires_executable_plan_before_approval": True,
        "validation_steps": ["inspect_existing_project", "build_executable_patch_or_project_generation_plan", "request_approval_after_plan"],
    }
    draft = TaskContractDraft(
        draft_id=f"phase_resume_{uuid4().hex}",
        session_id=session_id,
        status="preview_ready" if workspace_ref else "needs_clarification",
        intent_map={
            "operation": "phase_resume_implementation",
            "risk": "medium",
            "completed_phase": phase_resume.get("completed_phase") or "preflight",
            "next_phase": next_phase,
            "evidence_report_path": evidence_report_path,
            "target_path": workspace_ref,
            "prompt_summary": prompt[:500],
            "implementation_plan": implementation_plan,
            "approval_not_created_reason": "missing_executable_plan",
        },
        policy_decision={
            "decision_id": f"phase_resume_policy_{uuid4().hex}",
            "status": "allowed" if workspace_ref else "needs_clarification",
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": [],
            "granted_capabilities": [],
            "denied_capabilities": [],
        },
        contract_type="project_generation",
        operation_type="project_generation",
        intent_type="phase_resume_implementation",
        runtime_profile="project_generation",
        capabilities_required=["read_workspace", "validation"],
        source_scope="chat",
        requires_workspace=True,
        workspace=TaskDraftWorkspace(path=workspace_ref, status="confirmed" if workspace_ref else "missing"),
        requested_actions=[],
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=[],
        expected_outcomes=["implementation_plan"],
        safe_to_execute=False,
        safe_to_preview=bool(workspace_ref),
        clarifying_questions=[] if workspace_ref else ["Informe o workspace alvo para retomar a implementacao."],
        warnings=[] if workspace_ref else ["target_workspace_missing"],
        trace=[
            {
                "source": "api/routers/chat_router.py",
                "stage": "phase_resume",
                "decision": "implementation_plan_preview",
                "reason": "existing_report_used_as_evidence_without_rerunning_preflight",
                "operation_id": decision.operation_id,
                "evidence_report_path": evidence_report_path,
                "next_phase": next_phase,
            }
        ],
        created_at=now,
        updated_at=now,
    )
    draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    approval = None
    if not workspace_ref:
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="needs_clarification",
            message="Preciso do workspace alvo para retomar a implementacao a partir do relatorio existente.",
            intent={"intent_type": "phase_resume_implementation", "requires_task": True, "requires_workspace": True},
            policy={"workspace_write": True, "reason_code": "target_workspace_missing"},
            contract_preview={"draft": draft.model_dump(), "preview": preview.model_dump() if preview else None},
            operation_id=decision.operation_id,
            operation_type="governed_project_rebuild",
            message_type="clarification_request",
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            warnings=["target_workspace_missing"],
        )
    return ChatResponse(
        response_id=decision.operation_id,
        session_id=session_id,
        preview_id=preview.preview_id if preview else None,
        task_preview_id=preview.preview_id if preview else None,
        approval_id=approval.approval_id if approval else None,
        status="preview",
        message=(
            "STATUS: IMPLEMENTATION_PLAN_READY\n\n"
            "Usei o relatorio existente como evidencia de preflight concluido e criei um plano de implementacao conversacional. "
            "Ainda nao criei ApprovalRequest de escrita porque este preview nao contem um project_generation_plan executavel. "
            "Nada foi escrito ainda.\n\n"
            f"Fase concluida: {phase_resume.get('completed_phase') or 'preflight'}\n"
            f"Proxima fase: {next_phase}\n"
            f"Workspace: {workspace_ref}\n"
            f"Relatorio base: {evidence_report_path or 'nao informado'}\n"
            "Approval: nao criado; primeiro e necessario gerar plano executavel."
        ),
        intent={
            "intent_type": "phase_resume_implementation",
            "requires_task": True,
            "requires_workspace": True,
            "phase_resume": phase_resume,
        },
        policy={
            "workspace_write": True,
            "approval_required_for": [],
            "required_preconditions": ["existing_report_evidence", "executable_plan_before_approval", "approval", "validation"],
            "approval_not_created_reason": "missing_executable_plan",
            "safe_to_preview": True,
            "safe_to_execute": False,
        },
        contract_preview={
            "draft": draft.model_dump(),
            "preview": preview.model_dump() if preview else None,
            "approval": approval.model_dump() if approval else None,
        },
        operation_id=decision.operation_id,
        operation_type="governed_project_rebuild",
        message_type="task_preview",
        requires_user_action=True,
        is_final_answer=False,
        grounded=True,
        grounding_required=True,
        grounding_missing_reason="operation_preview_not_final_result",
        evidence_refs=[
            {"type": "report_file", "ref_id": evidence_report_path, "human_label": "Relatorio de fase anterior"},
            *(
                [{"type": "task_preview", "ref_id": preview.preview_id, "human_label": "Preview de implementacao"}]
                if preview
                else []
            ),
        ],
        next_actions=[
            ChatNextAction(type="create_executable_plan", label="Gerar plano executavel", target_id=preview.preview_id if preview else draft.draft_id),
            ChatNextAction(type="view_task_preview", label="Ver preview", target_id=preview.preview_id if preview else draft.draft_id),
        ],
    )


def _workspace_evidence_bundle_response(
    *,
    session_id: str,
    prompt: str,
    decision: ChatOperationDecision,
    request_metadata: dict[str, object],
    workspace_ref: str | None,
) -> ChatResponse:
    result = WorkspaceEvidenceBundleService().execute(WorkspaceEvidenceBundleRequest(
        session_id=session_id,
        operation_id=decision.operation_id,
        workspace_ref=str(workspace_ref or ""),
        prompt=prompt,
        summary_relative_path=str(decision.metadata.get("summary_relative_path") or ""),
        archive_relative_path=str(decision.metadata.get("archive_relative_path") or ""),
        source_relative_paths=[str(item) for item in decision.metadata.get("source_relative_paths", []) or []],
        include_globs=[str(item) for item in decision.metadata.get("include_globs", []) or []],
        title=str(decision.metadata.get("title") or "Evidence Bundle Summary"),
        execution_mode=str(request_metadata.get("execution_mode") or "governed_autorun"),
    ))
    if result.status == "completed":
        artifact_link = ChatArtifactLink(
            artifact_id=str(result.artifact_id),
            filename=Path(str(result.archive_path)).name,
            content_type="application/zip",
            size_bytes=Path(str(result.archive_path)).stat().st_size if result.archive_path and Path(result.archive_path).exists() else None,
            download_endpoint=str(result.download_endpoint or ""),
            download_path=str(result.download_endpoint or ""),
            label=f"Baixar {Path(str(result.archive_path)).name}",
        ) if result.artifact_id and result.archive_path else None
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=result.run_id,
            artifact_id=result.artifact_id,
            artifact_links=[artifact_link] if artifact_link else [],
            status="ok",
            message=(
                "STATUS: READY\n\n"
                "O resumo e o ZIP de evidencias foram criados pelo fluxo governado da AIpinho.\n\n"
                f"Resumo: {result.summary_path}\n"
                f"ZIP: {result.archive_path}\n"
                f"Entries validadas: {len(result.entries)}\n"
                f"Task/run: {result.run_id}\n"
                f"Tool summary: {result.summary_tool_invocation_id}\n"
                f"Tool archive: {result.archive_tool_invocation_id}\n"
                f"Validacao: {result.validation_status}"
            ),
            intent={"intent_type": "workspace_evidence_bundle", "requires_task": True, "requires_workspace": True},
            policy={"workspace_write": True, "tool_gateway": True, "validation_status": result.validation_status},
            operation_id=decision.operation_id,
            operation_type="workspace_evidence_bundle",
            message_type="assistant_final_answer",
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            grounding_required=True,
            evidence_refs=result.evidence_refs,
            next_actions=[ChatNextAction(type="download_artifact", label=artifact_link.label, target_id=artifact_link.artifact_id)] if artifact_link else [],
            warnings=result.warnings,
        )
    return ChatResponse(
        response_id=decision.operation_id,
        session_id=session_id,
        task_id=result.run_id,
        status="blocked" if result.status == "blocked" else "failed",
        message=f"STATUS: {'BLOCKED' if result.status == 'blocked' else 'FAILED'}\n\nA criacao do pacote governado nao foi concluida. Motivo: {result.reason_code or 'bundle_execution_failed'}.",
        intent={"intent_type": "workspace_evidence_bundle", "requires_task": True, "requires_workspace": True},
        policy={"workspace_write": True, "tool_gateway": True, "reason_code": result.reason_code},
        operation_id=decision.operation_id,
        operation_type="workspace_evidence_bundle",
        message_type="blocked_policy_message" if result.status == "blocked" else "assistant_degraded_answer",
        requires_user_action=False,
        is_final_answer=False,
        grounded=True,
        evidence_refs=result.evidence_refs,
        warnings=result.warnings,
    )


def _workspace_static_reachability_response(
    *,
    session_id: str,
    prompt: str,
    decision: ChatOperationDecision,
    request_metadata: dict[str, object],
    workspace_ref: str | None,
) -> ChatResponse:
    result = WorkspaceStaticReachabilityReportService().execute(WorkspaceStaticReachabilityReportRequest(
        session_id=session_id,
        operation_id=decision.operation_id,
        workspace_ref=str(workspace_ref or ""),
        prompt=prompt,
        expected_text=str(decision.metadata.get("expected_text") or ""),
        report_relative_path=str(decision.metadata.get("report_relative_path") or ""),
        execution_mode=str(request_metadata.get("execution_mode") or "governed_autorun"),
    ))
    if result.status in {"completed", "completed_with_warnings"}:
        verdict = "render_qa_passed_with_warning" if result.matched_files else "visual_qa_failed"
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=result.run_id,
            status="ok" if result.matched_files else "degraded",
            message=(
                f"STATUS: {'READY_WITH_WARNINGS' if result.matched_files else 'FAILED'}\n\n"
                "QA visual real nao ficou disponivel neste ambiente; executei QA de renderizacao/static reachability pelo fluxo governado.\n\n"
                f"Relatorio: {result.report_path}\n"
                f"Veredito: {verdict}\n"
                f"Matches: {len(result.matched_files)}\n"
                f"Task/run: {result.run_id}\n"
                f"Tool report: {result.report_tool_invocation_id}\n"
                f"Validacao: {result.validation_status}"
            ),
            intent={"intent_type": "workspace_static_reachability_report", "requires_task": True, "requires_workspace": True},
            policy={"workspace_write": True, "tool_gateway": True, "validation_status": result.validation_status},
            operation_id=decision.operation_id,
            operation_type="workspace_static_reachability_report",
            message_type="assistant_final_answer" if result.matched_files else "assistant_degraded_answer",
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            grounding_required=True,
            evidence_refs=result.evidence_refs,
            warnings=result.warnings,
        )
    return ChatResponse(
        response_id=decision.operation_id,
        session_id=session_id,
        task_id=result.run_id,
        status="blocked" if result.status == "blocked" else "failed",
        message=f"STATUS: {'BLOCKED' if result.status == 'blocked' else 'FAILED'}\n\nO QA static reachability nao foi concluido. Motivo: {result.reason_code or 'static_reachability_failed'}.",
        intent={"intent_type": "workspace_static_reachability_report", "requires_task": True, "requires_workspace": True},
        policy={"workspace_write": True, "tool_gateway": True, "reason_code": result.reason_code},
        operation_id=decision.operation_id,
        operation_type="workspace_static_reachability_report",
        message_type="blocked_policy_message" if result.status == "blocked" else "assistant_degraded_answer",
        requires_user_action=False,
        is_final_answer=False,
        grounded=True,
        evidence_refs=result.evidence_refs,
        warnings=result.warnings,
    )


def _workspace_readonly_audit_response(
    *,
    session_id: str,
    prompt: str,
    decision: ChatOperationDecision,
    request_metadata: dict[str, object],
    workspace_ref: str | None,
) -> ChatResponse:
    result = WorkspaceReadonlyAuditReportService().execute(WorkspaceReadonlyAuditReportRequest(
        session_id=session_id,
        operation_id=decision.operation_id,
        workspace_ref=str(workspace_ref or ""),
        prompt=prompt,
        report_relative_path=str(decision.metadata.get("report_relative_path") or ""),
        search_terms=[str(item) for item in decision.metadata.get("search_terms", []) or []],
        execution_mode=str(request_metadata.get("execution_mode") or "governed_autorun"),
    ))
    if result.status == "completed":
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=result.run_id,
            status="ok",
            message=(
                "STATUS: WORKSPACE_READONLY_AUDIT_READY\n\n"
                "Auditoria read-only concluida pelo fluxo governado.\n\n"
                f"Relatorio: {result.report_path}\n"
                f"Arquivos com matches: {len(result.matched_files)}\n"
                f"Matches: {result.match_count}\n"
                f"Task/run: {result.run_id}\n"
                f"Tool report: {result.report_tool_invocation_id}\n"
                f"Validacao: {result.validation_status}"
            ),
            intent={"intent_type": "workspace_readonly_audit_report", "requires_task": True, "requires_workspace": True},
            policy={"workspace_write": True, "workspace_write_scope": "requested_report_only", "tool_gateway": True, "validation_status": result.validation_status},
            operation_id=decision.operation_id,
            operation_type="workspace_readonly_audit_report",
            message_type="assistant_final_answer",
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            grounding_required=True,
            evidence_refs=result.evidence_refs,
            warnings=result.warnings,
        )
    return ChatResponse(
        response_id=decision.operation_id,
        session_id=session_id,
        task_id=result.run_id,
        status="blocked" if result.status == "blocked" else "failed",
        message=f"STATUS: {'BLOCKED' if result.status == 'blocked' else 'FAILED'}\n\nA auditoria read-only nao foi concluida. Motivo: {result.reason_code or 'workspace_readonly_audit_failed'}.",
        intent={"intent_type": "workspace_readonly_audit_report", "requires_task": True, "requires_workspace": True},
        policy={"workspace_write": True, "workspace_write_scope": "requested_report_only", "tool_gateway": True, "reason_code": result.reason_code},
        operation_id=decision.operation_id,
        operation_type="workspace_readonly_audit_report",
        message_type="blocked_policy_message" if result.status == "blocked" else "assistant_degraded_answer",
        requires_user_action=False,
        is_final_answer=False,
        grounded=True,
        evidence_refs=result.evidence_refs,
        warnings=result.warnings,
    )


def _try_persistent_chat_local_create_file(
    session_id: str,
    prompt: str,
    decision: ChatOperationDecision,
    request_metadata: dict[str, object],
) -> ChatResponse | None:
    workspace_context = str(
        request_metadata.get("workspace_context")
        or request_metadata.get("workspace_id")
        or request_metadata.get("_session_workspace_context")
        or decision.workspace
        or ""
    ).strip()
    requested_capabilities = [
        str(item)
        for item in (request_metadata.get("requested_capabilities") or [])
        if str(item).strip()
    ]
    if decision.operation_type != "governed_file_write" and not _looks_like_local_file_output_request(prompt, request_metadata, decision):
        return None
    return GovernedWriteChatService().from_decision(
        session_id=session_id,
        prompt=prompt,
        decision=decision,
        workspace_ref=workspace_context or decision.workspace,
        requested_capabilities=requested_capabilities,
        execution_mode=str(request_metadata.get("execution_mode") or "governed_autorun"),
    )


def _looks_like_local_file_output_request(
    prompt: str,
    request_metadata: dict[str, object],
    decision: ChatOperationDecision,
) -> bool:
    if "create_file" in {str(item) for item in (request_metadata.get("requested_capabilities") or [])}:
        return True
    lowered = prompt.casefold()
    local_output_markers = (
        "dentro desse diret",
        "dentro deste diret",
        "nesse diret",
        "neste diret",
        "na pasta",
        "nessa pasta",
        "nesta pasta",
        "no workspace",
        "inside that directory",
        "inside this directory",
        "in that folder",
        "in this folder",
    )
    return bool(decision.workspace and any(marker in lowered for marker in local_output_markers))


def _prompt_with_attachment_context(prompt: str, context_text: str) -> str:
    if not context_text.strip():
        return prompt
    return f"{prompt}\n\nContexto sanitizado de anexos enviados pelo usuario:{context_text}"


def _request_workspace_context(metadata: dict[str, object]) -> str | None:
    for key in ("workspace_context", "workspace_path", "workspace_ref", "active_workspace", "target_workspace"):
        candidate = _workspace_context_from_candidate((metadata or {}).get(key))
        if candidate:
            return candidate
    return None


def _latest_persistent_workspace_context(session_id: str) -> str | None:
    messages = ChatMessageService().list(session_id=session_id, limit=80)
    return _workspace_context_from_messages(messages)


def _workspace_context_from_messages(messages) -> str | None:
    for message in reversed(messages):
        metadata = getattr(message, "metadata", {}) or {}
        for key in ("workspace_context", "workspace_path", "workspace_ref", "active_workspace", "target_workspace"):
            candidate = _workspace_context_from_candidate(metadata.get(key))
            if candidate:
                return candidate
    extractor = PathExtractionService()
    for message in reversed(messages):
        if getattr(message, "role", None) != "user":
            continue
        paths = extractor.extract(str(getattr(message, "content", "") or ""))
        if paths:
            return paths[0].value
    for message in reversed(messages):
        metadata = getattr(message, "metadata", {}) or {}
        candidate = _workspace_context_from_candidate(metadata.get("file_path"))
        if candidate:
            return candidate
    return None


def _workspace_context_from_candidate(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    extracted = PathExtractionService().extract(text)
    if not extracted:
        return None
    path = Path(extracted[0].value)
    if path.suffix:
        path = path.parent
    return str(path)


def _decorate_attachment_response(response: ChatResponse, attachment_context) -> ChatResponse:
    if attachment_context is None or not attachment_context.artifact_ids:
        return response
    intent = dict(response.intent)
    intent["attached_artifact_ids"] = attachment_context.artifact_ids
    evidence = [*response.evidence_refs, *attachment_context.evidence_refs]
    warnings = list(dict.fromkeys([*response.warnings, *attachment_context.warnings]))
    return response.model_copy(update={"intent": intent, "evidence_refs": evidence, "warnings": warnings})


@router.post("/sessions/{session_id}/speaker/from-event/{event_id}")
def create_speaker_message(session_id: str, event_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "message": SpeakerMessageService().create_from_event(session_id, event_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="chat_session_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/timeline")
def chat_timeline(session_id: str) -> dict[str, object]:
    if ChatSessionService().get(session_id) is None:
        raise HTTPException(status_code=404, detail="chat_session_not_found")
    return {"status": "ok", "timeline": ChatTimelineService().timeline(session_id).model_dump()}


@router.get("/messages/{message_id}/copy")
def copy_chat_message(message_id: str) -> dict[str, object]:
    try:
        return {"status": "ok", "copy": ChatMessageService().copy(message_id).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="chat_message_not_found") from exc


@router.get("/messages/{message_id}/raw")
def chat_message_raw(message_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    message = ChatMessageService().get(message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="chat_message_not_found")
    if not message.raw_ref:
        raise HTTPException(status_code=404, detail="raw_payload_not_found")
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")
    return {"status": "ok", "raw": SanitizedRawService().read(message.raw_ref).model_dump()}


@router.get("/raw/{raw_ref}/copy")
def copy_raw_payload(raw_ref: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")
    try:
        return {"status": "ok", "copy": CopyActionService().copy_raw(raw_ref).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="raw_payload_not_found") from exc


@router.post("/messages/{message_id}/feedback")
def create_chat_message_feedback(message_id: str, request: FeedbackRequest) -> dict[str, object]:
    if request.target_id != message_id:
        raise HTTPException(status_code=409, detail="feedback_target_mismatch")
    if ChatMessageService().get(message_id) is None:
        raise HTTPException(status_code=404, detail="chat_message_not_found")
    return {"status": "ok", "feedback": FeedbackService().create(request).model_dump()}



