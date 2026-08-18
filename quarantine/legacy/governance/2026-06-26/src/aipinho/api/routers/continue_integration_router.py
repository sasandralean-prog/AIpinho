from __future__ import annotations

import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.schemas.tasks.task_preview import TaskPreview
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision, ChatOperationRouterService
from aipinho.services.governance.operation_contract_service import OperationContractService
from aipinho.services.models.capability_router_service import CapabilityRouterService
from aipinho.services.session.session_store import utc_now

router = APIRouter()

OPENAI_COMPAT_MODELS: dict[str, dict[str, str]] = {
    "aipinho-local": {"id": "aipinho-local", "object": "model", "owned_by": "aipinho"},
    "aipinho-agent": {"id": "aipinho-agent", "object": "model", "owned_by": "aipinho"},
}

CONTINUE_POLICY_PATH = PATHS.project_root / "config" / "integrations" / "continue_adapter_policy.json"
CONTINUE_DEFAULT_POLICY: dict[str, Any] = {
    "mode": "governed_dev",
    "allow_conversation": True,
    "allow_reasoning": True,
    "allow_context_analysis": True,
    "allow_context_read": True,
    "allow_workspace_read": True,
    "allow_patch_preview": True,
    "allow_task_preview": True,
    "allow_direct_write": False,
    "allow_direct_shell": False,
    "file_write_policy": "ask",
    "shell_policy": "ask",
    "delete_policy": "ask_strong",
    "git_push_policy": "ask_strong",
}

CONTINUE_SIDE_EFFECT_OPERATIONS = {
    "dangerous_operation_blocked",
    "filesystem_append_file",
    "filesystem_write_file",
    "filesystem_modify_file",
    "filesystem_delete_file",
    "sandbox_batch_artifact_request",
    "workspace_evidence_bundle",
    "workspace_static_reachability_report",
    "governed_configuration_change",
    "governed_change_plan",
    "governed_project_rebuild",
    "task_preview",
    "patch_preview",
    "patch_apply",
    "shell_command",
    "run_command",
    "artifact_request",
}

CONTINUE_SIDE_EFFECT_ACTIONS = {
    "apply_patch",
    "artifact_generate",
    "create_archive",
    "create_directory",
    "delete_file",
    "delete_files",
    "edit_config",
    "git_commit",
    "git_push",
    "move_file",
    "move_files",
    "patch",
    "patch_preview",
    "project_generation",
    "run_command",
    "run_shell",
    "shell",
    "validate_artifact",
    "write_file",
    "write_files",
    "workspace_write",
}

CONTINUE_CONTEXT_REFERENCE_PATTERN = re.compile(
    r"(?is)(?:^|\s)@(?P<name>Git\s+Diff|Terminal|[A-Za-z0-9_.\\/\- ]+\.[A-Za-z0-9_]+|rules/[A-Za-z0-9_.\\/\-]+)"
)
CONTINUE_MATH_EXPRESSION_PATTERN = re.compile(
    r"(?is)(?:quanto\s+(?:e|eh|é)|calcule|calculate|what\s+is)\s*(?P<expr>[0-9\s+\-*/().,xX×÷]+)"
)
CONTINUE_CAPABILITY_PATTERN = re.compile(
    r"(?is)\b(?:voce|você|you)?\s*(?:consegue|pode|can\s+you)\b.*\b(?:ler|read|arquivo|file|workspace|contexto|context)\b"
)
CONTINUE_HOW_TO_CONFIGURE_PATTERN = re.compile(
    r"(?is)\b(?:como|how)\b.*\b(?:configur|liberar|habilitar|ativar|enable|configure|personali|tom|tone|policy|policies|recursos|features)\b"
)
CONTINUE_CAPABILITY_CONFIGURATION_PATTERN = re.compile(
    r"(?is)\b(?:consegue|pode|can\s+you)\b.*\b(?:configur|liberar|habilitar|ativar|enable|configure|personali|tom|tone|recursos|features)\b"
)
CONTINUE_CONTEXT_ANALYSIS_PATTERN = re.compile(
    r"(?is)\b(?:explique|analis|resum|summari[sz]e|explain|review|o que este|what does)\b.*\b(?:arquivo|file|diff|terminal|contexto|context|erro|code|codigo|código)\b"
)
CONTINUE_FILE_WRITE_PATTERN = re.compile(
    r"(?is)\b(?:crie|criar|grave|gravar|salve|salvar|altere|alterar|modifique|modificar|edite|editar|"
    r"delete|deletar|apague|apagar|remova|remover|mova|mover|write|create|modify|edit|remove|delete)\b"
    r".{0,90}\b(?:arquivo|file|pasta|folder|workspace|disco|disk|path|c:\\|\.tsx|\.ts|\.js|\.py|\.md|\.json)\b"
)
CONTINUE_PATCH_PATTERN = re.compile(r"(?is)\b(?:patch|diff|aplique|aplicar|apply)\b")
CONTINUE_SHELL_PATTERN = re.compile(
    r"(?is)\b(?:rode|rodar|execute|executar|run)\b.{0,80}\b(?:shell|terminal|comando|command|npm|pytest|python|gradle|mvn|powershell|cmd)\b"
)
CONTINUE_DANGEROUS_PATTERN = re.compile(r"(?is)\b(?:git\s+push|push|commit|delete|deletar|apague|apagar|remove|remova|mova|mover)\b")
CONTINUE_WINDOWS_PATH_PATTERN = re.compile(
    r"(?i)(?:[A-Z]:\\[^\s\"'<>|]+|[A-Z]:/[^\s\"'<>|]+)"
)
CONTINUE_RELATIVE_TARGET_PATTERN = re.compile(
    r"(?i)\b(?:[\w.-]+[\\/])*[\w.-]+\.(?:md|txt|json|ya?ml|py|js|ts|tsx|jsx|kt|java|cs|ps1|bat|sh|html|css)\b"
)


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


class ContinueChatIntegrationRequest(BaseModel):
    model: str = "aipinho-local"
    messages: list[OpenAIMessage]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    user: str | None = None
    source: str | None = None
    mode: str = "chat"
    workspace_path: str | None = None


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


def _messages_to_prompt(messages: list[OpenAIMessage]) -> str:
    return "\n\n".join(f"{message.role}: {message.content}" for message in messages)


def _last_user_prompt(messages: list[OpenAIMessage]) -> str:
    for message in reversed(messages):
        if message.role.lower() == "user":
            return message.content.strip()
    return _messages_to_prompt(messages).strip()


def _continue_session_id(request: OpenAIChatCompletionRequest) -> str:
    raw_user = (request.user or "default").strip() or "default"
    safe_user = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_user)[:80]
    return f"continue_{safe_user}"


def _continue_policy() -> dict[str, Any]:
    policy = dict(CONTINUE_DEFAULT_POLICY)
    try:
        if CONTINUE_POLICY_PATH.exists():
            loaded = json.loads(CONTINUE_POLICY_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                policy.update(loaded)
    except Exception:
        policy["policy_load_warning"] = "continue_adapter_policy_unreadable"

    env_to_key = {
        "CONTINUE_MODE": "mode",
        "CONTINUE_ALLOW_CONVERSATION": "allow_conversation",
        "CONTINUE_ALLOW_REASONING": "allow_reasoning",
        "CONTINUE_ALLOW_CONTEXT_ANALYSIS": "allow_context_analysis",
        "CONTINUE_ALLOW_CONTEXT_READ": "allow_context_read",
        "CONTINUE_ALLOW_WORKSPACE_READ": "allow_workspace_read",
        "CONTINUE_ALLOW_PATCH_PREVIEW": "allow_patch_preview",
        "CONTINUE_ALLOW_TASK_PREVIEW": "allow_task_preview",
        "CONTINUE_ALLOW_DIRECT_WRITE": "allow_direct_write",
        "CONTINUE_ALLOW_DIRECT_SHELL": "allow_direct_shell",
        "CONTINUE_FILE_WRITE_POLICY": "file_write_policy",
        "CONTINUE_SHELL_POLICY": "shell_policy",
        "CONTINUE_DELETE_POLICY": "delete_policy",
        "CONTINUE_GIT_PUSH_POLICY": "git_push_policy",
    }
    for env_name, key in env_to_key.items():
        raw_value = os.getenv(env_name)
        if raw_value is None:
            continue
        normalized = raw_value.strip()
        if normalized.lower() in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
            policy[key] = normalized.lower() in {"true", "1", "yes", "on"}
        else:
            policy[key] = normalized
    return policy


def _parse_continue_context(messages: list[OpenAIMessage]) -> dict[str, Any]:
    full_prompt = _messages_to_prompt(messages)
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in CONTINUE_CONTEXT_REFERENCE_PATTERN.finditer(full_prompt):
        name = " ".join(match.group("name").strip().split())
        lower = name.lower()
        if lower == "terminal":
            kind = "terminal"
        elif lower == "git diff":
            kind = "git_diff"
        elif lower.startswith("rules/"):
            kind = "rule"
        else:
            kind = "file"
        key = (kind, name)
        if key not in seen:
            seen.add(key)
            items.append({"kind": kind, "name": name})
    return {
        "has_context": bool(items),
        "items": items,
        "item_names": [item["name"] for item in items],
        "kinds": sorted({item["kind"] for item in items}),
        "full_prompt": full_prompt,
    }


def _record_continue_event(event_type: str, metadata: dict[str, Any] | None = None) -> None:
    event = {
        "event_id": f"continue_event_{uuid4().hex}",
        "event_type": event_type,
        "created_at": utc_now(),
        "metadata": _sanitize_continue_metadata(metadata or {}),
    }
    path = PATHS.project_root / "data" / "runtime" / "continue" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _sanitize_continue_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(secret_word in key_text.lower() for secret_word in ("key", "token", "secret", "authorization")):
                sanitized[key_text] = "[REDACTED]"
            else:
                sanitized[key_text] = _sanitize_continue_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_continue_metadata(item) for item in value]
    if isinstance(value, str):
        return value[:1024]
    return value


def _validate_openai_compat_model(model: str) -> None:
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


def _validate_continue_auth(authorization: str | None) -> None:
    configured_token = os.getenv("CONTINUE_API_TOKEN", "").strip()
    if not configured_token:
        return
    allowed_tokens = {configured_token}
    allow_dummy = os.getenv("CONTINUE_ALLOW_LOCAL_DUMMY_TOKEN", "true").strip().lower() in {"1", "true", "yes", "on"}
    if allow_dummy:
        allowed_tokens.add("aipinho-local-token")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "continue_auth_required", "message": "Authorization Bearer token required."}},
        )
    token = authorization.split(" ", 1)[1].strip()
    if token not in allowed_tokens:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "continue_auth_invalid", "message": "Invalid Continue adapter token."}},
        )


def _completion_response(
    *,
    model: str,
    content: str,
    finish_reason: str = "stop",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "id": f"chatcmpl_{uuid4().hex}",
        "object": "chat.completion",
        "created": int(datetime.utcnow().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    if metadata:
        response["aipinho"] = metadata
    return response


def _completion_chunk(chat_id: str, *, model: str, created: int, delta: dict[str, str], finish_reason: str | None) -> dict[str, Any]:
    return {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def _iter_text_chunks(content: str, chunk_size: int = 240) -> Iterator[str]:
    if not content:
        yield ""
        return
    for offset in range(0, len(content), chunk_size):
        yield content[offset : offset + chunk_size]


def _stream_completion_response(*, model: str, content: str) -> StreamingResponse:
    chat_id = f"chatcmpl_{uuid4().hex}"
    created = int(datetime.utcnow().timestamp())

    def event_stream() -> Iterator[str]:
        role_chunk = _completion_chunk(chat_id, model=model, created=created, delta={"role": "assistant"}, finish_reason=None)
        yield f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n"
        for text_chunk in _iter_text_chunks(content):
            content_chunk = _completion_chunk(chat_id, model=model, created=created, delta={"content": text_chunk}, finish_reason=None)
            yield f"data: {json.dumps(content_chunk, ensure_ascii=False)}\n\n"
        finish_chunk = _completion_chunk(chat_id, model=model, created=created, delta={}, finish_reason="stop")
        yield f"data: {json.dumps(finish_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _direct_answer_from_instruction(prompt: str) -> str | None:
    match = re.search(r"(?is)\b(?:responda|responder|reply|answer)\s+(?:apenas|somente|only)\s*:?\s*(.+?)\s*$", prompt)
    if not match:
        return None
    answer = match.group(1).strip().strip('"').strip("'").strip()
    if not answer or len(answer) > 1000:
        return None
    return answer


def _safe_eval_math_expression(expression: str) -> str | None:
    normalized = expression.replace(",", ".").replace("×", "*").replace("÷", "/").replace("x", "*").replace("X", "*")
    normalized = re.sub(r"\s+", "", normalized)
    if not normalized or len(normalized) > 80 or not re.fullmatch(r"[0-9+\-*/().]+", normalized):
        return None
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError:
        return None

    def eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = eval_node(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = eval_node(node.left)
            right = eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if right == 0:
                raise ValueError("division_by_zero")
            return left / right
        raise ValueError("unsupported_math_expression")

    try:
        result = eval_node(tree)
    except Exception:
        return None
    if result.is_integer():
        result_text = str(int(result))
    else:
        result_text = f"{result:.6g}"
    return f"{normalized} = {result_text}."


def _math_answer_from_prompt(prompt: str) -> str | None:
    match = CONTINUE_MATH_EXPRESSION_PATTERN.search(prompt)
    if not match:
        return None
    return _safe_eval_math_expression(match.group("expr"))


def _classify_continue_intent(prompt: str, context: dict[str, Any]) -> str:
    if _math_answer_from_prompt(prompt) is not None:
        return "math_or_reasoning"
    if CONTINUE_HOW_TO_CONFIGURE_PATTERN.search(prompt) or CONTINUE_CAPABILITY_CONFIGURATION_PATTERN.search(prompt):
        return "how_to_configure"
    if CONTINUE_CAPABILITY_PATTERN.search(prompt):
        return "conversation"
    if context.get("has_context") and CONTINUE_CONTEXT_ANALYSIS_PATTERN.search(prompt):
        return "continue_context_analysis"
    if context.get("has_context"):
        return "continue_context_analysis"
    if CONTINUE_SHELL_PATTERN.search(prompt):
        return "shell_request"
    if CONTINUE_DANGEROUS_PATTERN.search(prompt):
        return "dangerous_operation_request"
    if CONTINUE_FILE_WRITE_PATTERN.search(prompt):
        return "file_write_request"
    if CONTINUE_PATCH_PATTERN.search(prompt):
        return "patch_preview_request"
    return "conversation"


def _capability_aware_answer(policy: dict[str, Any]) -> str:
    workspace_read = "posso solicitar leitura governada de arquivos do workspace" if policy.get("allow_workspace_read") else "leitura adicional do workspace esta desabilitada"
    return (
        "Consigo analisar arquivos que o Continue anexar ao contexto. "
        f"Tambem {workspace_read} conforme a policy. "
        "Para alterar arquivos, aplicar patch ou rodar shell, preciso usar preview, approval e validacao quando aplicavel."
    )


def _configuration_guidance_answer(policy: dict[str, Any]) -> str:
    flags = [
        f"CONTINUE_MODE={policy.get('mode', 'governed_dev')}",
        f"CONTINUE_ALLOW_CONTEXT_READ={str(bool(policy.get('allow_context_read'))).lower()}",
        f"CONTINUE_ALLOW_WORKSPACE_READ={str(bool(policy.get('allow_workspace_read'))).lower()}",
        f"CONTINUE_ALLOW_PATCH_PREVIEW={str(bool(policy.get('allow_patch_preview'))).lower()}",
        f"CONTINUE_ALLOW_DIRECT_WRITE={str(bool(policy.get('allow_direct_write'))).lower()}",
        f"CONTINUE_ALLOW_DIRECT_SHELL={str(bool(policy.get('allow_direct_shell'))).lower()}",
        f"CONTINUE_FILE_WRITE_POLICY={policy.get('file_write_policy', 'ask')}",
        f"CONTINUE_SHELL_POLICY={policy.get('shell_policy', 'ask')}",
    ]
    return (
        "Consigo orientar essa configuracao. Para o Continue atuar como assistente de programacao governado, "
        "mantenha conversa, raciocinio e analise de contexto liberados, e deixe escrita/shell em preview/approval. "
        "Flags principais:\n"
        + "\n".join(f"- {flag}" for flag in flags)
        + "\n\nSe voce quiser persistir uma mudanca real nesses arquivos de config, eu devo preparar uma alteracao governada em vez de escrever direto por esta rota."
    )


def _context_analysis_answer(context: dict[str, Any], policy: dict[str, Any]) -> str:
    items = context.get("items") or []
    if not items:
        return _capability_aware_answer(policy)
    grouped: dict[str, list[str]] = {}
    for item in items:
        grouped.setdefault(str(item.get("kind", "context")), []).append(str(item.get("name", "contexto")))
    parts = []
    for kind, names in grouped.items():
        label = {
            "file": "arquivos",
            "terminal": "terminal",
            "git_diff": "git diff",
            "rule": "regras",
        }.get(kind, kind)
        parts.append(f"{label}: {', '.join(names[:6])}")
    return (
        "Recebi contexto anexado pelo Continue (" + "; ".join(parts) + "). "
        "Posso analisar com base nesse conteudo sem alegar que nao consigo ler arquivos. "
        "Para buscar arquivos adicionais no disco, uso leitura governada conforme policy; para alterar algo, preparo preview/approval."
    )


def _governed_action_message(intent: str, policy: dict[str, Any]) -> str:
    if intent == "shell_request":
        action = "execucao de shell"
        policy_value = policy.get("shell_policy", "ask")
    elif intent == "dangerous_operation_request":
        action = "acao destrutiva ou git/write sensivel"
        policy_value = policy.get("delete_policy", "ask_strong")
    elif intent == "patch_preview_request":
        action = "patch ou diff"
        policy_value = "preview" if policy.get("allow_patch_preview") else "ask"
    else:
        action = "criacao ou alteracao de arquivo"
        policy_value = policy.get("file_write_policy", "ask")
    return (
        f"Posso ajudar com {action}, mas nao executo efeito colateral direto por esta resposta do Continue. "
        f"Politica atual: {policy_value}. Posso descrever o plano, sugerir o patch em texto ou abrir o caminho governado "
        "de preview, approval e validacao pela AIpinho."
    )


def _decision_requests_side_effect(decision: ChatOperationDecision) -> bool:
    metadata = decision.metadata or {}
    if decision.operation_type in CONTINUE_SIDE_EFFECT_OPERATIONS:
        return True
    if decision.message_type in {"task_preview", "task_status_update", "blocked_policy_message"}:
        requested_operation = str(metadata.get("requested_operation", ""))
        if requested_operation in CONTINUE_SIDE_EFFECT_ACTIONS:
            return True
    if metadata.get("workspace_write") is True or metadata.get("requires_patch") is True:
        return True
    requested_actions = metadata.get("requested_actions")
    if isinstance(requested_actions, list) and any(str(action) in CONTINUE_SIDE_EFFECT_ACTIONS for action in requested_actions):
        return True
    return False


def _continue_action_for_intent(intent: str) -> str:
    if intent == "shell_request":
        return "run_command"
    return "write_files"


def _continue_contract_type_for_action(action_type: str) -> str:
    if action_type == "run_command":
        return "validation_request"
    return "patch_request"


def _continue_workspace_from_prompt(prompt: str, target_paths: list[str]) -> str | None:
    explicit_paths = CONTINUE_WINDOWS_PATH_PATTERN.findall(prompt)
    if explicit_paths:
        path = Path(explicit_paths[0].strip().strip(".,;"))
        return str(path.parent if path.suffix else path)
    for target in target_paths:
        path = Path(target)
        if path.is_absolute():
            return str(path.parent if path.suffix else path)
    return None


def _continue_target_paths(prompt: str) -> list[str]:
    targets: list[str] = []
    for match in CONTINUE_WINDOWS_PATH_PATTERN.finditer(prompt):
        value = match.group(0).strip().strip(".,;")
        if value and value not in targets:
            targets.append(value)
    for match in CONTINUE_RELATIVE_TARGET_PATTERN.finditer(prompt):
        value = match.group(0).strip().strip(".,;")
        if value and value not in targets:
            targets.append(value)
    return targets


def _continue_command_from_prompt(prompt: str) -> str | None:
    match = re.search(r"(?is)\b(?:rode|rodar|execute|executar|run)\s+(?P<command>.+?)\s*$", prompt)
    if not match:
        return None
    command = " ".join(match.group("command").strip().split())
    return command[:500] if command else None


def _build_continue_chat_action_draft(
    *,
    session_id: str,
    prompt: str,
    intent: str,
    action_type: str,
    target_paths: list[str],
    command: str | None,
) -> TaskContractDraft:
    draft_id = f"continue_action_{uuid4().hex}"
    workspace_path = _continue_workspace_from_prompt(prompt, target_paths)
    workspace = TaskDraftWorkspace(path=workspace_path, status="confirmed" if workspace_path else "missing")
    operation_contract = OperationContractService().build(
        source_channel="vscode_continue",
        source_client="continue",
        session_id=session_id,
        user_text=prompt,
        intent_type=intent,
        operation_type=action_type,
        requested_actions=[action_type],
        workspace_refs=[workspace_path] if workspace_path else [],
        target_paths=target_paths,
        command=command,
        operation_id=draft_id,
    )
    policy_decision = {
        "decision_id": f"continue_policy_{uuid4().hex}",
        "status": "needs_approval",
        "allowed_actions": [],
        "denied_actions": [],
        "approval_required_for": [action_type],
        "granted_capabilities": [],
        "denied_capabilities": [],
        "operation_contract_id": operation_contract.operation_id,
    }
    trace = [
        {
            "source": "continue_openai_compat",
            "stage": "approval_request",
            "intent": intent,
            "action_type": action_type,
            "execution_allowed": False,
        }
    ]
    return TaskContractDraft(
        draft_id=draft_id,
        session_id=session_id,
        status="approval_required",
        intent_map={
            "prompt": prompt,
            "source_channel": "vscode_continue",
            "intent": intent,
            "risk": "high" if action_type == "run_command" else "medium",
            "target_paths": target_paths,
            "command": command,
            "operation_contract": operation_contract.model_dump(),
        },
        policy_decision=policy_decision,
        contract_type=_continue_contract_type_for_action(action_type),
        operation_type=action_type,
        intent_type="continue_chat_action",
        runtime_profile="governed",
        capabilities_required=[action_type],
        source_scope="vscode_continue",
        requires_workspace=bool(workspace_path),
        workspace=workspace,
        requested_actions=[action_type],
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=[action_type],
        safe_to_execute=False,
        safe_to_preview=True,
        clarifying_questions=[],
        warnings=[] if workspace_path or action_type == "run_command" else ["workspace_not_explicit_in_continue_request"],
        trace=trace,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def _approval_required_text(approval: ApprovalRequest, *, action_type: str, command: str | None) -> str:
    action_label = "execucao de shell" if action_type == "run_command" else "criacao/alteracao de arquivo"
    targets = ", ".join(approval.target_paths) if approval.target_paths else "sem arquivo alvo explicito"
    command_text = command or ", ".join(approval.commands) or "sem comando extraido"
    return (
        "APPROVAL REQUIRED\n\n"
        f"approval_id: {approval.approval_id}\n"
        f"acao: {action_type} ({action_label})\n"
        f"workspace: {approval.workspace_path or 'workspace nao informado'}\n"
        f"arquivos: {targets}\n"
        f"comando: {command_text if action_type == 'run_command' else 'n/a'}\n"
        f"risco: {approval.risk_level}\n"
        "policy: ask\n\n"
        "Nada foi executado ainda. Para aprovar, responda:\n"
        f"APROVAR {approval.approval_id}\n\n"
        "Para negar:\n"
        f"NEGAR {approval.approval_id}\n\n"
        "Para detalhes:\n"
        f"MOSTRAR PREVIEW {approval.approval_id}"
    )


def _continue_approval_required_response(
    *,
    prompt: str,
    intent: str,
    policy: dict[str, Any],
    decision: ChatOperationDecision,
    session_id: str | None,
    stream: bool,
) -> tuple[str, dict[str, Any]]:
    action_type = _continue_action_for_intent(intent)
    command = _continue_command_from_prompt(prompt) if action_type == "run_command" else None
    target_paths = _continue_target_paths(prompt)
    draft = _build_continue_chat_action_draft(
        session_id=session_id or "continue_default",
        prompt=prompt,
        intent=intent,
        action_type=action_type,
        target_paths=target_paths,
        command=command,
    )
    if draft.workspace.path is None:
        draft.workspace.status = "not_required"
        draft.requires_workspace = False
        draft.warnings = list(dict.fromkeys([*draft.warnings, "workspace_must_be_resolved_before_execution"]))
    draft_store = TaskDraftStore()
    preview_service = TaskPreviewService(draft_store=draft_store)
    approval_service = ApprovalService(preview_service=preview_service, draft_store=draft_store)
    draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    if preview is None:
        raise RuntimeError("continue_preview_generation_failed")
    approval = approval_service.create_approval_for_preview(
        preview.preview_id,
        actions=[action_type],
        reason="Continue chat requested governed side effect approval",
    )
    if action_type == "run_command" and command:
        approval.commands = [command]
        approval_service.store.save(approval)
    approval_service.append_event(
        approval.approval_id,
        "approval_request_created",
        "ApprovalRequest real criado a partir do chat Continue.",
        {
            "source_channel": "vscode_continue",
            "session_id": session_id,
            "operation_id": preview.preview_id,
            "approval_id": approval.approval_id,
            "action_type": action_type,
            "risk_level": approval.risk_level,
            "policy_decision": preview.policy_snapshot.model_dump(),
        },
    )
    approval_service.append_event(
        approval.approval_id,
        "continue_approval_required",
        "Continue solicitou approval textual; nenhuma acao local foi executada.",
        {
            "source_channel": "vscode_continue",
            "session_id": session_id,
            "continue_intent": intent,
            "target_paths": approval.target_paths,
            "command": command,
        },
    )
    content = _approval_required_text(approval, action_type=action_type, command=command)
    return (
        content,
        {
            "route": "continue_openai_compat",
            "execution_allowed": False,
            "reason_code": "continue_approval_required",
            "continue_intent": intent,
            "operation_type": decision.operation_type,
            "policy_mode": policy.get("mode"),
            "approval_id": approval.approval_id,
            "preview_id": preview.preview_id,
            "draft_id": draft.draft_id,
            "action_type": action_type,
            "operation_contract": (draft.intent_map.get("operation_contract") if isinstance(draft.intent_map, dict) else None),
            "stream": stream,
        },
    )


def _resolve_continue_content(messages: list[OpenAIMessage], model: str, *, stream: bool, session_id: str | None = None) -> tuple[str, dict[str, Any]]:
    prompt = _last_user_prompt(messages)
    context = _parse_continue_context(messages)
    policy = _continue_policy()
    intent = _classify_continue_intent(prompt, context)
    decision = ChatOperationRouterService().route(prompt)
    route_preview = CapabilityRouterService().route_preview(
        operation_type=f"continue_{intent}" if not intent.startswith("continue_") else intent,
        intent_type=intent,
        source_channel="vscode_continue",
    )
    route_decision = route_preview.get("route_decision", {})

    if intent in {"file_write_request", "shell_request"}:
        return _continue_approval_required_response(
            prompt=prompt,
            intent=intent,
            policy=policy,
            decision=decision,
            session_id=session_id,
            stream=stream,
        )
    if intent == "dangerous_operation_request":
        return (
            _governed_action_message(intent, policy)
            + "\n\nOperacoes destrutivas ou git write exigem pedido explicito, preview governado e approval especifico. Nenhuma acao local foi executada.",
            {
                "route": "continue_openai_compat",
                "execution_allowed": False,
                "reason_code": "continue_dangerous_action_requires_strong_approval_flow",
                "continue_intent": intent,
                "operation_type": decision.operation_type,
                "policy_mode": policy.get("mode"),
                "stream": stream,
                "model_route_decision": route_decision,
            },
        )
    if intent == "patch_preview_request" and not policy.get("allow_patch_preview"):
        return (
            _governed_action_message(intent, policy),
            {
                "route": "continue_openai_compat",
                "execution_allowed": False,
                "reason_code": "continue_patch_preview_disabled",
                "continue_intent": intent,
                "operation_type": decision.operation_type,
                "policy_mode": policy.get("mode"),
                "stream": stream,
                "model_route_decision": route_decision,
            },
        )

    direct_answer = _direct_answer_from_instruction(prompt)
    if direct_answer is not None:
        content = direct_answer
    elif intent == "math_or_reasoning":
        content = _math_answer_from_prompt(prompt) or "Nao consegui resolver essa expressao com seguranca nesta rota."
    elif intent == "how_to_configure":
        content = _configuration_guidance_answer(policy)
    elif CONTINUE_CAPABILITY_PATTERN.search(prompt):
        content = _capability_aware_answer(policy)
    elif intent == "continue_context_analysis":
        content = _context_analysis_answer(context, policy)
    else:
        chat_request = ChatRequest(
            message=prompt,
            model_id=None,
            context=ChatContext(surface="api"),
        )
        chat_response = ChatService().respond(chat_request)
        content = chat_response.message or "Recebi a mensagem, mas a rota conversacional nao retornou texto."

    return (
        content,
        {
            "route": "continue_openai_compat",
            "execution_allowed": False,
            "continue_intent": intent,
            "context_items": context.get("items", []),
            "policy_mode": policy.get("mode"),
            "stream": stream,
            "model_route_decision": route_decision,
        },
    )


def _validate_vscode_source(source: str | None) -> None:
    if source != "vscode_continue":
        raise HTTPException(status_code=400, detail="invalid_source; expected 'vscode_continue'")


def _contract_type_for_action(action_type: str) -> str:
    if action_type in {"create_file", "modify_file", "delete_file", "move_file", "apply_patch", "write_files"}:
        return "patch_request"
    if action_type in {"run_shell", "run_command", "git_commit", "git_push"}:
        return "validation_request"
    return "patch_request"


def _build_vscode_action_draft(request: VscodeActionPreviewRequest, draft_id: str) -> TaskContractDraft:
    workspace = TaskDraftWorkspace(path=request.workspace_path, status="confirmed")
    policy_decision = {
        "decision_id": f"policy_decision_{uuid4().hex}",
        "status": "pending",
        "allowed_actions": [],
        "denied_actions": [],
        "approval_required_for": [request.action_type],
        "granted_capabilities": [],
        "denied_capabilities": [],
    }
    return TaskContractDraft(
        draft_id=draft_id,
        session_id=None,
        status="approval_required",
        intent_map={
            "action_request": request.model_dump(),
            "risk": "high" if request.action_type in {"run_shell", "git_commit", "git_push"} else "medium",
        },
        policy_decision=policy_decision,
        contract_type=_contract_type_for_action(request.action_type),
        operation_type=request.action_type,
        intent_type="vscode_continue_action",
        runtime_profile="governed",
        capabilities_required=[request.action_type],
        source_scope="vscode_continue",
        requires_workspace=True,
        workspace=workspace,
        requested_actions=[request.action_type],
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=[request.action_type],
        safe_to_execute=False,
        safe_to_preview=True,
        clarifying_questions=[],
        warnings=[],
        trace=[{"source": "vscode_continue", "action_type": request.action_type}],
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def _preview_summary_response(preview: TaskPreview, approval: ApprovalRequest | None = None, request: VscodeActionPreviewRequest | None = None) -> dict[str, Any]:
    return {
        "status": preview.status,
        "operation_id": preview.preview_id,
        "approval_id": approval.approval_id if approval is not None else None,
        "risk_level": preview.policy_snapshot.risk_level,
        "policy_decision": preview.policy_snapshot.model_dump(),
        "preview": preview.model_dump(),
        "diff": {
            "action_type": request.action_type if request is not None else None,
            "target_paths": request.target_paths if request is not None else None,
            "source_paths": request.source_paths if request is not None else None,
            "command": request.command if request is not None else None,
            "patch": bool(request.patch) if request is not None else None,
            "content_preview": (request.content[:320] if request is not None and request.content else None),
        },
        "message": preview.summary,
    }


def _find_approval_for_preview(preview_id: str) -> ApprovalRequest | None:
    approvals = ApprovalService().list_approvals(limit=500)
    for approval in approvals:
        if approval.preview_id == preview_id:
            return approval
    return None


@router.get("/v1/models")
def list_models() -> dict[str, Any]:
    _record_continue_event("continue_model_list_requested", {"model_count": len(OPENAI_COMPAT_MODELS)})
    return {
        "object": "list",
        "data": list(OPENAI_COMPAT_MODELS.values()),
    }


@router.get("/v1/models/{model_id}")
def get_model(model_id: str) -> dict[str, Any]:
    _validate_openai_compat_model(model_id)
    _record_continue_event("continue_model_list_requested", {"model_id": model_id})
    return {**OPENAI_COMPAT_MODELS[model_id], "permission": []}


@router.post("/v1/chat/completions", response_model=None)
def create_chat_completion(request: OpenAIChatCompletionRequest, authorization: str | None = Header(default=None)) -> dict[str, Any] | StreamingResponse:
    _validate_continue_auth(authorization)
    _validate_openai_compat_model(request.model)
    prompt = _last_user_prompt(request.messages)
    session_id = _continue_session_id(request)
    _record_continue_event(
        "continue_chat_completion_requested",
        {"model": request.model, "stream": request.stream, "message_count": len(request.messages), "session_id": session_id},
    )
    try:
        approval_response = ChatApprovalCommandService().handle(
            session_id,
            prompt,
            source_channel="vscode_continue",
        )
        if approval_response is not None:
            metadata = {
                "route": "continue_openai_compat",
                "approval_command": True,
                "approval_id": approval_response.approval_id,
                "status": approval_response.status,
                "source_channel": "vscode_continue",
                "stream": request.stream,
            }
            _record_continue_event(
                "continue_approval_decision_received",
                {
                    "model": request.model,
                    "stream": request.stream,
                    "approval_id": approval_response.approval_id,
                    "status": approval_response.status,
                    "session_id": session_id,
                },
            )
            if request.stream:
                return _stream_completion_response(model=request.model, content=approval_response.message)
            return _completion_response(
                model=request.model,
                content=approval_response.message,
                metadata={**metadata, "stream_fallback": False},
            )

        content, metadata = _resolve_continue_content(request.messages, request.model, stream=request.stream, session_id=session_id)
        if request.stream:
            _record_continue_event(
                "continue_response_sent",
                {
                    "model": request.model,
                    "stream": True,
                    "blocked_side_effect": metadata.get("reason_code")
                    in {"continue_governed_action_requires_preview_approval", "continue_patch_preview_disabled"},
                    "continue_intent": metadata.get("continue_intent"),
                },
            )
            return _stream_completion_response(model=request.model, content=content)

        response = _completion_response(
            model=request.model,
            content=content,
            metadata={**metadata, "stream_fallback": False},
        )
        _record_continue_event(
            "continue_response_sent",
                {
                    "model": request.model,
                    "stream": False,
                    "blocked_side_effect": metadata.get("reason_code")
                    in {"continue_governed_action_requires_preview_approval", "continue_patch_preview_disabled"},
                    "continue_intent": metadata.get("continue_intent"),
                },
            )
        return response
    except HTTPException:
        _record_continue_event("continue_request_failed", {"model": request.model, "error_type": "http_exception"})
        raise
    except Exception as exc:
        _record_continue_event(
            "continue_request_failed",
            {"model": request.model, "error_type": type(exc).__name__, "reason": str(exc)[:240]},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "A rota OpenAI-compatible da AIpinho falhou de forma controlada.",
                    "type": "server_error",
                    "code": "continue_chat_completion_failed",
                }
            },
        ) from exc


@router.post("/v1/integrations/continue/chat")
def create_continue_chat(request: ContinueChatIntegrationRequest) -> dict[str, Any]:
    _validate_openai_compat_model(request.model)
    prompt = _last_user_prompt(request.messages)
    chat_request = ChatRequest(
        message=prompt,
        model_id=None,
        context=ChatContext(surface="api", active_workspace=request.workspace_path),
    )
    chat_response = ChatService().respond(chat_request)

    return _completion_response(
        model=request.model,
        content=chat_response.message,
        metadata={"route": "continue_legacy_chat", "stream_fallback": bool(request.stream)},
    )


@router.post("/v1/integrations/vscode/actions/preview")
def create_vscode_action_preview(request: VscodeActionPreviewRequest) -> dict[str, Any]:
    _validate_vscode_source(request.source)
    draft_id = f"vscode_action_{uuid4().hex}"
    draft = _build_vscode_action_draft(request, draft_id)
    TaskDraftStore().save(draft)
    preview = TaskPreviewService().create_preview_from_draft(draft_id)
    if preview is None:
        raise HTTPException(status_code=500, detail="preview_generation_failed")
    approval: ApprovalRequest | None = None
    if preview.status == "approval_required":
        approval = ApprovalService().create_approval_for_preview(preview.preview_id, reason=request.reason or "VS Code Continue action preview requested")
    return _preview_summary_response(preview, approval, request)


@router.post("/v1/integrations/vscode/actions/execute")
def execute_vscode_action(request: VscodeActionExecuteRequest) -> dict[str, Any]:
    _validate_vscode_source(request.source)
    raise HTTPException(
        status_code=403,
        detail={
            "error": "continue_action_execute_disabled",
            "reason_code": "continue_connection_phase_no_write_or_shell",
            "message": "Execucao local via Continue esta desabilitada nesta fase. Use o fluxo governado da AIpinho para preview, approval, apply e validation.",
        },
    )
