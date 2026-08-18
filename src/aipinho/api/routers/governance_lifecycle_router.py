from __future__ import annotations

import json
import hashlib
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.schemas.chat.manual_chat_inference_response import ManualChatInferenceResponse
from aipinho.schemas.interaction.contracts import (
    ChatMessageCreateRequest,
    ChatSessionCreateRequest,
    ChatSessionRenameRequest,
    FeedbackRequest,
)
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.chat.chat_attachment_context_service import ChatAttachmentContextService
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision, ChatOperationRouterService
from aipinho.services.chat.chat_persistence_gate_service import ChatPersistenceGateService
from aipinho.services.chat.chat_result_index_service import ChatResultIndexService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.chat_manual_inference_service import ChatManualInferenceService
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.governance.lifecycle.public_route_lifecycle_service import PublicRouteLifecycleService
from aipinho.services.interaction.interaction_core import (
    ChatMessageService,
    ChatSessionService,
    ChatTimelineService,
    CopyActionService,
    FeedbackService,
    SanitizedRawService,
    SpeakerMessageService,
)
from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.runtime.runtime_state_hygiene_service import RuntimeStateHygieneService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.roles.role_pipeline_service import RolePipelineService


router = APIRouter(tags=["canonical-governance-lifecycle"])

OPENAI_COMPAT_MODELS: dict[str, dict[str, str]] = {
    "aipinho-local": {"id": "aipinho-local", "object": "model", "owned_by": "aipinho"},
    "aipinho-agent": {"id": "aipinho-agent", "object": "model", "owned_by": "aipinho"},
}


class OpenAIMessage(BaseModel):
    role: str
    content: str


class OpenAIChatCompletionRequest(BaseModel):
    model: str
    messages: list[OpenAIMessage]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    user: str | None = None


class ChatApprovalCommandRequest(BaseModel):
    session_id: str
    text: str
    message_id: str | None = None
    source_channel: str = "api"


class VscodeActionPreviewRequest(BaseModel):
    workspace_path: str
    action_type: str
    target_paths: list[str] = Field(default_factory=list)
    source_paths: list[str] = Field(default_factory=list)
    command: str | None = None
    patch: str | None = None
    content: str | None = None
    reason: str | None = None
    source: str


class VscodeActionExecuteRequest(BaseModel):
    approval_id: str | None = None
    preview_id: str | None = None
    workspace_path: str | None = None
    source: str


@router.get("/api/v1/governance/lifecycle/status")
def lifecycle_status() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "canonical_governance_lifecycle",
        "source_of_truth": "GovernanceLifecycleSnapshot",
        "public_routes_rewired": [
            "POST /api/v1/chat",
            "POST /api/v1/chat/preview",
            "POST /api/v1/chat/approval-command",
            "POST /api/v1/chat/sessions/{session_id}/send",
            "POST /v1/chat/completions",
            "POST /v1/integrations/continue/chat",
        ],
    }


@router.get("/api/v1/chat/status")
def get_chat_status() -> dict[str, object]:
    runtime = TaskRuntimeService().status()
    roles = RolePipelineService().status()
    return {
        "status": "ok",
        "service": "canonical_chat",
        "source_of_truth": "GovernanceLifecycleSnapshot",
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


@router.get("/api/v1/chat/diagnostics")
def get_chat_diagnostics() -> dict[str, object]:
    status = ChatService().status()
    return {
        "status": "ok",
        "service": "canonical_chat_diagnostics",
        "legacy_content_provider": status,
        "runtime_fingerprint": _runtime_fingerprint(),
    }


def _runtime_fingerprint() -> dict[str, object]:
    modules = [
        "services/governance/runtime/readonly_analysis_artifact_runtime_service.py",
        "services/artifacts/observed_entity_compilation_service.py",
        "services/artifacts/contract_driven_perception_service.py",
        "services/cvl/cognitive_validation_laboratory_service.py",
    ]
    root = Path(__file__).resolve().parents[2]
    rows: list[dict[str, object]] = []
    digest = hashlib.sha256()
    for module in modules:
        path = root / module
        try:
            stat = path.stat()
            data = path.read_bytes()
        except OSError:
            rows.append({"module": module, "status": "missing"})
            continue
        module_hash = hashlib.sha256(data).hexdigest()
        digest.update(module.encode("utf-8"))
        digest.update(module_hash.encode("utf-8"))
        rows.append(
            {
                "module": module,
                "status": "loaded",
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "sha256": module_hash,
            }
        )
    return {
        "fingerprint": digest.hexdigest(),
        "modules": rows,
        "purpose": "detect_stale_public_runtime_wiring",
    }


@router.get("/api/v1/chat/model-status")
def get_chat_model_status() -> dict[str, object]:
    return ChatModelPolicyService().status()


@router.post("/api/v1/chat/manual-inference/preview")
def post_chat_manual_inference_preview(request: ManualChatInferenceRequest) -> ManualChatInferenceResponse:
    return ChatManualInferenceService().preview(request)


@router.post("/api/v1/chat/manual-inference")
def post_chat_manual_inference(request: ManualChatInferenceRequest) -> ManualChatInferenceResponse:
    return ChatManualInferenceService().run(request)


@router.post("/api/v1/chat")
def post_chat(request: ChatRequest) -> ChatResponse:
    try:
        return CanonicalPublicChatService().respond(request, source_channel="api_chat")
    except ValueError as exc:
        if str(exc) == "invalid_session_id":
            raise HTTPException(status_code=409, detail="invalid_session_id") from exc
        raise


@router.post("/api/v1/chat/preview")
def post_chat_preview(request: ChatRequest) -> ChatResponse:
    preview_request = request.model_copy(update={"mode": "preview", "include_trace": True})
    return CanonicalPublicChatService().respond(preview_request, source_channel="api_chat_preview")


@router.post("/api/v1/chat/approval-command")
def post_chat_approval_command(request: ChatApprovalCommandRequest) -> dict[str, object]:
    response = ChatApprovalCommandService().handle(
        request.session_id,
        request.text,
        source_channel=request.source_channel,
        message_id=request.message_id,
    )
    if response is None:
        return {"status": "not_found", "approval_id": None, "message": "Nenhum comando de approval reconhecido."}
    response = PublicRouteLifecycleService().finalize_chat_response(
        response,
        prompt=request.text,
        source_channel=request.source_channel,
    )
    return {
        "status": response.status,
        "approval_id": response.approval_id,
        "message": response.message,
        "chat_response": response.model_dump(),
    }


@router.post("/api/v1/chat/sessions")
def create_chat_session(request: ChatSessionCreateRequest) -> dict[str, object]:
    return {"status": "ok", "session": ChatSessionService().create(request).model_dump()}


@router.get("/api/v1/chat/sessions")
def list_chat_sessions(limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> dict[str, object]:
    sessions = sorted(ChatSessionService().list(), key=lambda session: session.updated_at, reverse=True)
    selected = sessions[offset: offset + limit]
    return {"status": "ok", "total": len(sessions), "limit": limit, "offset": offset, "sessions": [session.model_dump() for session in selected]}


@router.get("/api/v1/chat/sessions/{session_id}")
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


@router.patch("/api/v1/chat/sessions/{session_id}")
def rename_chat_session(session_id: str, request: ChatSessionRenameRequest) -> dict[str, object]:
    return _rename_chat_session_payload(session_id, request)


@router.post("/api/v1/chat/sessions/{session_id}/rename")
def rename_chat_session_post(session_id: str, request: ChatSessionRenameRequest) -> dict[str, object]:
    return _rename_chat_session_payload(session_id, request)


@router.delete("/api/v1/chat/sessions/{session_id}")
def delete_chat_session(session_id: str) -> dict[str, object]:
    service = ChatSessionService()
    if service.get(session_id) is None:
        raise HTTPException(status_code=404, detail="chat_session_not_found")
    deleted_messages = ChatMessageService().delete_for_session(session_id)
    deleted = service.delete(session_id)
    return {"status": "ok", "deleted": deleted, "session_id": session_id, "deleted_messages": deleted_messages}


@router.post("/api/v1/chat/sessions/{session_id}/messages")
def create_chat_message(session_id: str, request: ChatMessageCreateRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "message": ChatMessageService().create(session_id, request).model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="chat_session_not_found") from exc


@router.post("/api/v1/chat/sessions/{session_id}/send")
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
                metadata={**request.metadata, "source": "canonical_persistent_chat_send"},
            ),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="chat_session_not_found") from exc
    surface = str(request.metadata.get("source_channel") or request.metadata.get("source") or "launcher_or_mobile_chat")
    workspace = _workspace_from_metadata(request.metadata)
    attachment_context = ChatAttachmentContextService().from_metadata(request.metadata)
    effective_content = request.content
    if attachment_context.context_text:
        effective_content = (
            f"{request.content}\n\n"
            "Contexto sanitizado de anexos governados:"
            f"{attachment_context.context_text}"
        )
    queue_health = RuntimeStateHygieneService().queue_health()
    backpressure_applies = queue_health.get("backpressure_required") and not _bypasses_task_backpressure(effective_content, workspace)
    if backpressure_applies:
        reason_code = str(queue_health.get("reason_code") or "dispatcher_saturated")
        chat_response = ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=session_id,
            operation_type="chat_dispatch",
            message_type="assistant_degraded_answer",
            status="degraded",
            message=(
                "CHAT_DISPATCH_DEGRADED\n"
                f"reason_code: {reason_code}\n"
                "Sua mensagem foi registrada, mas a fila de execucao esta sem slot disponivel. "
                "Libere runs antigas ou aguarde o dispatcher recuperar capacidade."
            ),
            intent={"intent_type": "chat_dispatch", "requires_task": False},
            policy={"permission": "not_applicable", "reason_code": reason_code},
            warnings=[reason_code],
            governance_lifecycle={"queue_health": queue_health},
            is_final_answer=True,
            grounded=True,
            model_used="runtime_state_hygiene",
            real_inference=False,
            fallback_used=False,
        )
    else:
        chat_response = CanonicalPublicChatService().respond(
            ChatRequest(
                message=effective_content,
                session_id=session_id,
                mode="normal",
                include_trace=False,
                context=ChatContext(surface="mobile", active_workspace=workspace),
            ),
            source_channel="persistent_chat",
        )
    if attachment_context.artifact_ids:
        intent = dict(chat_response.intent)
        intent["attached_artifact_ids"] = list(attachment_context.artifact_ids)
        evidence_refs = [*chat_response.evidence_refs, *attachment_context.evidence_refs]
        warnings = list(dict.fromkeys([*chat_response.warnings, *attachment_context.warnings]))
        chat_response = chat_response.model_copy(
            update={
                "intent": intent,
                "evidence_refs": evidence_refs,
                "warnings": warnings,
            }
        )
    if (
        chat_response.result_ref_id is None
        and chat_response.is_final_answer
        and chat_response.grounded
        and chat_response.status in {"ok", "ready"}
    ):
        chat_response = chat_response.model_copy(update={"result_ref_id": f"result_{uuid4().hex}"})
    metadata_decision = ChatOperationDecision(
        operation_id=chat_response.operation_id or f"chatop_{uuid4().hex}",
        operation_type=chat_response.operation_type or str(chat_response.intent.get("intent_type") or "conversation"),
        message_type=chat_response.message_type,
        confidence=1.0,
    )
    assistant_metadata = ChatPersistenceGateService().metadata(chat_response, metadata_decision)
    assistant_metadata.update(
        {
            "chat_response": chat_response.model_dump(),
            "source": "canonical_persistent_chat_send",
            "source_channel": surface,
        }
    )
    assistant_message = message_service.create(
        session_id,
        ChatMessageCreateRequest(
            role="assistant",
            content=chat_response.message,
            task_id=chat_response.task_id,
            metadata=assistant_metadata,
        ),
    )
    if chat_response.result_ref_id:
        indexed = ChatResultIndexService().add_final_answer(session_id, chat_response, assistant_message.message_id)
        if indexed and indexed != chat_response.result_ref_id:
            chat_response = chat_response.model_copy(update={"result_ref_id": indexed})
    return {
        "status": "ok",
        "user_message": user_message.model_dump(),
        "assistant_message": assistant_message.model_dump(),
        "chat_response": chat_response.model_dump(),
        "timeline": ChatTimelineService().timeline(session_id).model_dump(),
    }


def _bypasses_task_backpressure(content: str, workspace: str | None) -> bool:
    decision = ChatOperationRouterService().route(content, workspace_hint=workspace)
    routed_type = str(decision.metadata.get("router_operation_type") or decision.operation_type)
    if routed_type in {
        "workspace_permission_list",
        "permission_status",
        "session_diagnostic",
        "followup_result_recall",
        "followup_result_review",
        "artifact_request",
        "filesystem_archive_request",
    }:
        return True
    return bool(decision.metadata.get("requires_task") is False and decision.metadata.get("read_only") is True)


@router.get("/api/v1/chat/sessions/{session_id}/timeline")
def chat_timeline(session_id: str) -> dict[str, object]:
    return {"status": "ok", "timeline": ChatTimelineService().timeline(session_id).model_dump()}


@router.post("/api/v1/chat/sessions/{session_id}/speaker/from-event/{event_id}")
def create_speaker_message(session_id: str, event_id: str) -> dict[str, object]:
    message = SpeakerMessageService().create_from_event(session_id, event_id)
    return {"status": "ok", "message": message.model_dump()}


@router.get("/api/v1/chat/messages/{message_id}/copy")
def copy_chat_message(message_id: str) -> dict[str, object]:
    return {"status": "ok", "copy": CopyActionService().message(message_id).model_dump()}


@router.get("/api/v1/chat/messages/{message_id}/raw")
def chat_message_raw(message_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    token = LocalTokenService().from_authorization_header(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="token_required")
    return {"status": "ok", "raw": SanitizedRawService().message(message_id).model_dump()}


@router.get("/api/v1/chat/raw/{raw_ref}/copy")
def copy_raw_ref(raw_ref: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    token = LocalTokenService().from_authorization_header(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="token_required")
    return {"status": "ok", "copy": CopyActionService().raw(raw_ref).model_dump()}


@router.post("/api/v1/chat/messages/{message_id}/feedback")
def create_chat_message_feedback(message_id: str, request: FeedbackRequest) -> dict[str, object]:
    return {"status": "ok", "feedback": FeedbackService().create(message_id, request).model_dump()}


@router.get("/v1/models")
def list_models() -> dict[str, Any]:
    return {"object": "list", "data": list(OPENAI_COMPAT_MODELS.values())}


@router.get("/v1/models/{model_id}")
def get_model(model_id: str) -> dict[str, Any]:
    _validate_model(model_id)
    return {**OPENAI_COMPAT_MODELS[model_id], "permission": []}


@router.post("/v1/chat/completions", response_model=None)
def create_chat_completion(request: OpenAIChatCompletionRequest, authorization: str | None = Header(default=None)) -> dict[str, Any] | StreamingResponse:
    _validate_model(request.model)
    prompt = _last_user_prompt(request.messages)
    session_id = _continue_session_id(request)
    response = CanonicalPublicChatService().respond(
        ChatRequest(
            message=prompt,
            session_id=session_id,
            context=ChatContext(surface="api"),
        ),
        source_channel="vscode_continue",
    )
    if request.stream:
        return _stream_completion_response(model=request.model, content=response.message, metadata=response.governance_lifecycle)
    return _completion_response(model=request.model, content=response.message, metadata={"route": "canonical_continue", "governance_lifecycle": response.governance_lifecycle})


@router.post("/v1/integrations/continue/chat")
def create_continue_chat(request: OpenAIChatCompletionRequest) -> dict[str, Any]:
    _validate_model(request.model)
    prompt = _last_user_prompt(request.messages)
    response = CanonicalPublicChatService().respond(
        ChatRequest(message=prompt, context=ChatContext(surface="api")),
        source_channel="vscode_continue",
    )
    return _completion_response(model=request.model, content=response.message, metadata={"route": "canonical_continue_legacy", "governance_lifecycle": response.governance_lifecycle})


@router.post("/v1/integrations/vscode/actions/preview")
def create_vscode_action_preview(request: VscodeActionPreviewRequest) -> dict[str, Any]:
    _validate_vscode_source(request.source)
    prompt = _vscode_action_prompt(request)
    response = CanonicalPublicChatService().respond(
        ChatRequest(
            message=prompt,
            context=ChatContext(surface="api", active_workspace=request.workspace_path),
            include_trace=True,
        ),
        source_channel="vscode_continue_action_preview",
    )
    preview = TaskPreviewService().get_preview(response.preview_id) if response.preview_id else None
    return {
        "status": response.status,
        "operation_id": response.preview_id or response.operation_id,
        "approval_id": response.approval_id,
        "risk_level": (preview.policy_snapshot.risk_level if preview is not None else response.governance_lifecycle.get("operation_contract", {}).get("risk_level")),
        "policy_decision": (preview.policy_snapshot.model_dump() if preview is not None else response.policy.get("canonical_lifecycle", {})),
        "preview": preview.model_dump() if preview is not None else response.contract_preview,
        "diff": {
            "action_type": request.action_type,
            "target_paths": request.target_paths,
            "source_paths": request.source_paths,
            "command": request.command,
            "patch": bool(request.patch),
            "content_preview": request.content[:320] if request.content else None,
        },
        "message": response.message,
        "governance_lifecycle": response.governance_lifecycle,
        "canonical_route": True,
    }


@router.post("/v1/integrations/vscode/actions/execute")
def execute_vscode_action(request: VscodeActionExecuteRequest) -> dict[str, Any]:
    _validate_vscode_source(request.source)
    if not request.approval_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "approval_id_required",
                "reason_code": "continue_execute_requires_approval_id",
                "message": "Continue execute precisa de approval_id. Crie preview/approval antes de pedir execucao.",
            },
        )
    try:
        decision, approval = ApprovalService().approve(
            request.approval_id,
            reason="VS Code Continue action execute approved through canonical governance route",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "approval_execute_not_accepted",
                "reason_code": str(exc),
                "message": "A decisao de approval nao foi aceita; nenhuma execucao local foi iniciada.",
            },
        ) from exc
    return {
        "status": "approved",
        "approval_id": approval.approval_id,
        "preview_id": approval.preview_id,
        "draft_id": approval.draft_id,
        "execution_status": approval.execution_status,
        "message": "Approval registrado pela rota canonica. A execucao real continua limitada ao runtime governado/queue; este endpoint nao executa shell nem escrita diretamente.",
        "decision": decision.model_dump(),
        "approval": approval.model_dump(),
        "canonical_route": True,
    }


def _workspace_from_metadata(metadata: dict[str, Any]) -> str | None:
    for key in ("active_workspace", "workspace", "workspace_path"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    context = metadata.get("workspace_context")
    if isinstance(context, dict):
        value = context.get("path") or context.get("workspace") or context.get("workspace_path")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _validate_vscode_source(source: str | None) -> None:
    if source != "vscode_continue":
        raise HTTPException(status_code=400, detail="invalid_source; expected 'vscode_continue'")


def _vscode_action_prompt(request: VscodeActionPreviewRequest) -> str:
    targets = ", ".join(request.target_paths) if request.target_paths else request.workspace_path
    if request.action_type in {"run_shell", "run_command", "shell"}:
        return f"Executar comando governado no workspace {request.workspace_path}: {request.command or ''}"
    if request.action_type in {"apply_patch", "patch", "patch_preview"}:
        return f"Apply_patch governado no workspace {request.workspace_path}. Alvos: {targets}. Patch: {request.patch or ''}"
    if request.action_type in {"create_directory", "mkdir"}:
        return f"Crie uma pasta dentro de {request.workspace_path}. Alvos: {targets}."
    return f"Criar ou alterar arquivo governado no workspace {request.workspace_path}. Alvos: {targets}. Conteudo: {request.content or ''}"


def _last_user_prompt(messages: list[OpenAIMessage]) -> str:
    for message in reversed(messages):
        if message.role.lower() == "user":
            return message.content.strip()
    return "\n\n".join(f"{message.role}: {message.content}" for message in messages).strip()


def _continue_session_id(request: OpenAIChatCompletionRequest) -> str:
    raw_user = (request.user or "default").strip() or "default"
    safe_user = "".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in raw_user)[:80]
    return f"chat_continue_{safe_user}"


def _validate_model(model: str) -> None:
    if model not in OPENAI_COMPAT_MODELS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Modelo local nao disponivel nesta rota: {model}",
                    "type": "invalid_request_error",
                    "code": "model_not_found",
                    "available_models": sorted(OPENAI_COMPAT_MODELS),
                }
            },
        )


def _completion_response(*, model: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {
        "id": f"chatcmpl_{uuid4().hex}",
        "object": "chat.completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    if metadata:
        response["aipinho"] = metadata
    return response


def _stream_completion_response(*, model: str, content: str, metadata: dict[str, Any] | None = None) -> StreamingResponse:
    chat_id = f"chatcmpl_{uuid4().hex}"
    created = int(datetime.utcnow().timestamp())

    def event_stream() -> Iterator[str]:
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}], 'aipinho': metadata or {}}, ensure_ascii=False)}\n\n"
        for offset in range(0, len(content), 240):
            chunk = content[offset : offset + 240]
            yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'id': chat_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
