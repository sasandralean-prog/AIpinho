from __future__ import annotations

import re
import unicodedata
from typing import Any
from uuid import uuid4

from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.services.chat.session_grant_service import SessionGrantService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.governance.operation_contract_service import OperationContractService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


class ChatPermissionGrantService:
    """Parses chat-native permission grant requests.

    This service does not mutate persistent policy. Permanent requests are
    surfaced as config-change previews; temporary grants become pending
    SessionGrant records that still need explicit approval.
    """

    _PATH_RE = re.compile(r"(?P<path>[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\?)+)")
    _GRANT_TERMS = (
        "dou permissao",
        "dar permissao",
        "permissao para",
        "permissoes para",
        "permitir",
        "liberar",
        "autorizo",
        "pode escrever",
        "pode criar",
        "pode ler",
        "libere",
        "habilite",
    )
    _PERMANENT_TERMS = ("permanente", "sempre", "config", "registry", "registrar")
    _SESSION_TERMS = ("esta sessao", "ate o fim desta sessao", "durante esta sessao")
    _TASK_TERMS = ("esta task", "esta tarefa", "durante esta tarefa")
    _SINGLE_USE_TERMS = ("so esta vez", "somente esta vez", "uma vez")
    _SAFE_READONLY_INTENT_TERMS = (
        "product_planning_readonly",
        "planning_readonly",
        "analysis_only",
        "read_only_plan",
        "somente planejamento textual",
        "nao implementar nada agora",
        "nao escreva arquivos",
        "nao escrever arquivos",
        "nao criar approvalrequest",
        "nao criar approval request",
        "nao criar grant",
        "nao e pedido para criar grant",
        "nao e pedido para escrever arquivo",
        "nao e configchangerequest",
        "nao e pedido para alterar configuracao",
    )
    _NEGATED_GRANT_TERMS = (
        "nao e pedido para criar grant",
        "nao criar grant",
        "nao e pedido para escrever arquivo",
        "nao escrever arquivo",
        "nao escrever arquivos",
        "nao crie approvalrequest",
        "nao criar approvalrequest",
        "nao criar approval request",
        "nao e pedido para criar approvalrequest",
        "nao e pedido para criar approval request",
        "nao e configchangerequest",
        "nao e pedido para alterar configuracao",
    )

    def __init__(
        self,
        *,
        grants: SessionGrantService | None = None,
        matrix: WorkspacePermissionMatrixService | None = None,
        operation_contracts: OperationContractService | None = None,
        semantic_intent: SemanticIntentResolutionService | None = None,
    ) -> None:
        self.grants = grants or SessionGrantService()
        self.matrix = matrix or WorkspacePermissionMatrixService().load()
        self.operation_contracts = operation_contracts or OperationContractService(permission_matrix=self.matrix)
        self.semantic_intent = semantic_intent or SemanticIntentResolutionService()

    def handle(
        self,
        *,
        session_id: str,
        text: str,
        source_channel: str = "api",
        active_workspace: str | None = None,
    ) -> ChatResponse | None:
        semantic = self.semantic_intent.resolve(text, source_channel=source_channel)
        if semantic.intent_type != "permission_grant_request":
            return None
        normalized = self._normalize(text)
        if not self._has_positive_grant(normalized):
            return None
        actions = self._actions(normalized)
        if not actions:
            return None
        path = self._path(text) or active_workspace
        if not path:
            return ChatResponse(
                response_id=f"grant_{uuid4().hex}",
                session_id=session_id,
                status="needs_clarification",
                message="Entendi o pedido de permissao, mas preciso do workspace ou caminho que essa permissao deve cobrir.",
                intent={"intent_type": "permission_grant_request", "requires_task": False},
                operation_type="session_permission_grant",
                message_type="clarification_request",
                actions=actions,
                requires_user_action=True,
                next_actions=[ChatNextAction(type="provide_workspace", label="Informar workspace")],
                warnings=["workspace_required_for_permission_grant"],
            )
        contract = self.operation_contracts.build(
            source_channel=source_channel,
            source_client=source_channel,
            session_id=session_id,
            user_text=text,
            intent_type="permission_grant_request",
            operation_type="config_permission_grant" if self._is_permanent(normalized) else "session_permission_grant",
            requested_actions=actions,
            workspace_refs=[path],
        )
        if self._is_permanent(normalized):
            return self._config_preview_response(session_id, text, source_channel, path, actions, contract.model_dump())
        decision = self.matrix.decide(path=path, permission=actions[0])
        grant = self.grants.create_pending(
            session_id=session_id,
            workspace_id=decision.workspace_id,
            workspace_path=decision.root_path or path,
            actions=actions,
            paths_scope=[decision.root_path or path],
            command_scope=self._command_scope(text, normalized),
            scope=self._scope(normalized),
            source_channel=source_channel,
            reason="chat_native_permission_grant_request",
            max_uses=None if self._scope(normalized) in {"session", "task"} else 1,
            evidence=[
                {"type": "workspace_permission_decision", "decision": decision.model_dump()},
                {"type": "operation_contract", "operation_id": contract.operation_id},
            ],
        )
        return ChatResponse(
            response_id=f"grant_{uuid4().hex}",
            session_id=session_id,
            status="pending_approval",
            message=(
                "Criei um pedido de permissao temporaria. "
                f"Grant: {grant.grant_id}. Escopo: {grant.scope}. "
                "Para conceder, envie APROVAR GRANT "
                f"{grant.grant_id}; para negar, envie NEGAR GRANT {grant.grant_id}."
            ),
            intent={"intent_type": "permission_grant_request", "requires_task": False},
            policy={
                "requires_user_approval": True,
                "grant_id": grant.grant_id,
                "workspace_id": grant.workspace_id,
                "operation_contract_id": contract.operation_id,
            },
            contract_preview={"grant": grant.model_dump(), "operation_contract": contract.model_dump()},
            operation_id=contract.operation_id,
            operation_type="session_permission_grant",
            message_type="task_preview",
            actions=actions,
            next_actions=[
                ChatNextAction(type="approve_grant", label="Aprovar permissao", target_id=grant.grant_id),
                ChatNextAction(type="deny_grant", label="Negar permissao", target_id=grant.grant_id),
                ChatNextAction(type="change_scope", label="Alterar escopo", target_id=grant.grant_id),
            ],
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            evidence_refs=[{"type": "session_grant", "ref_id": grant.grant_id}],
        )

    def _config_preview_response(self, session_id: str, text: str, source_channel: str, path: str, actions: list[str], contract: dict[str, Any]) -> ChatResponse:
        return ChatResponse(
            response_id=f"config_grant_{uuid4().hex}",
            session_id=session_id,
            status="preview",
            message=(
                "O pedido parece permanente. Nao alterei configuracao automaticamente. "
                "Para tornar isso persistente, o fluxo precisa criar ConfigChangeRequest com preview, approval, backup, apply e self-check."
            ),
            intent={"intent_type": "config_permission_grant_request", "requires_task": False},
            policy={"requires_config_change_request": True, "source_channel": source_channel},
            contract_preview={
                "requested_workspace": path,
                "requested_actions": actions,
                "operation_contract": contract,
                "next_required_flow": "config_change_preview_approval_backup_apply_self_check",
                "source_text": text,
            },
            operation_id=str(contract.get("operation_id") or f"op_{uuid4().hex}"),
            operation_type="config_permission_grant_preview",
            message_type="task_preview",
            actions=actions,
            next_actions=[ChatNextAction(type="create_config_change_request", label="Criar preview de configuracao")],
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            warnings=["persistent_policy_change_requires_config_change_request"],
        )

    def _actions(self, normalized: str) -> list[str]:
        actions: list[str] = []
        if any(term in normalized for term in ("ler", "leitura", "read")):
            actions.extend(["read_file", "list_files"])
        if any(term in normalized for term in ("criar", "create", "escrever", "write")):
            actions.append("create_file")
        if any(term in normalized for term in ("alterar", "modificar", "editar", "patch")):
            actions.append("modify_file")
        if any(term in normalized for term in ("shell build", "build", "gradlew", "assemble")):
            actions.append("shell_build")
        elif "shell" in normalized or "comando" in normalized:
            actions.append("shell_readonly")
        if any(term in normalized for term in ("deletar", "excluir", "apagar", "delete")) and any(term in normalized for term in ("explicitamente", "confirmo delete", "confirmo deletar")):
            actions.append("delete_file")
        return list(dict.fromkeys(actions))

    def _path(self, text: str) -> str | None:
        quoted = re.search(r"[`\"](?P<path>[A-Za-z]:\\[^`\"\r\n]+)[`\"]", text or "")
        if quoted:
            return quoted.group("path").strip().strip('`"')
        match = self._PATH_RE.search(text or "")
        if not match:
            return None
        value = match.group("path").strip().strip('`"')
        for marker in (" e ", " para ", " durante ", " com ", " que ", ". ", ";"):
            if marker in value:
                value = value.split(marker, 1)[0]
        return value.rstrip(".,;: ")

    def _scope(self, normalized: str) -> str:
        if any(term in normalized for term in self._SESSION_TERMS):
            return "session"
        if any(term in normalized for term in self._TASK_TERMS):
            return "task"
        if any(term in normalized for term in self._SINGLE_USE_TERMS):
            return "single_use"
        return "single_use"

    def _command_scope(self, text: str, normalized: str) -> list[str]:
        if "gradlew" not in normalized and "comando" not in normalized:
            return []
        command_match = re.search(r"(?:comando|para)\s+[`\"]?(?P<command>[^`\"\r\n]+)[`\"]?", text, re.IGNORECASE)
        return [command_match.group("command").strip()] if command_match else []

    def _is_permanent(self, normalized: str) -> bool:
        return any(term in normalized for term in self._PERMANENT_TERMS)

    def _is_explicit_readonly_planning(self, normalized: str) -> bool:
        return any(term in normalized for term in self._SAFE_READONLY_INTENT_TERMS)

    def _has_negated_grant_terms(self, normalized: str) -> bool:
        return any(term in normalized for term in self._NEGATED_GRANT_TERMS)

    def _has_positive_grant(self, normalized: str) -> bool:
        if not any(term in normalized for term in self._GRANT_TERMS):
            return False
        positive_patterns = (
            r"\b(?:eu\s+)?dou permissao\b",
            r"\b(?:eu\s+)?concedo\b",
            r"\b(?:eu\s+)?autorizo\b",
            r"\b(?:eu\s+)?permito\b",
            r"\bpermissao\s+para\s+(?:ler|escrever|criar|alterar|modificar|rodar|executar)\b",
            r"\bautorizar\b",
            r"\bliberar\b",
            r"\blibere\b",
            r"\bhabilite\b",
            r"\bpermitir\b",
            r"\bpode\s+(?:escrever|criar|ler|alterar|modificar|rodar|executar)\b",
        )
        return any(re.search(pattern, normalized) for pattern in positive_patterns)

    def _normalize(self, text: str) -> str:
        value = unicodedata.normalize("NFKD", text or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return " ".join(value.casefold().split())
