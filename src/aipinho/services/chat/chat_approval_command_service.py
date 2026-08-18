from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_task_continuation_service import ApprovalTaskContinuationService
from aipinho.services.chat.session_grant_service import SessionGrantService


@dataclass(frozen=True)
class ApprovalCommand:
    action: str
    target_id: str | None
    target_kind: str
    scope: str
    detail_type: str | None = None
    strong_action: str | None = None
    source_text: str = ""


class ChatApprovalCommandService:
    """Handles explicit approval commands typed in chat.

    The parser intentionally requires a concrete approval_id or task/run id.
    Vague permission requests remain normal chat/task requests and never become
    blanket approvals.
    """

    _APPROVAL_ID = r"approval_[A-Za-z0-9_-]+"
    _GRANT_ID = r"grant_[A-Za-z0-9_-]+"
    _APPROVAL_RE = re.compile(
        r"^\s*(?P<action>aprovar|aprove|approve|negar|rejeitar|deny|reject|cancelar|cancel)\s+"
        r"(?:(?P<strong>delete|deletar|move|mover|git\s+push)\s+)?"
        rf"(?P<target>{_APPROVAL_ID})\s*$",
        re.IGNORECASE,
    )
    _GRANT_RE = re.compile(
        r"^\s*(?P<action>aprovar|aprove|approve|negar|rejeitar|deny|reject|cancelar|cancel)\s+"
        r"(?:grant|permiss[aÃ£]o|permissao)\s+"
        rf"(?P<target>{_GRANT_ID})\s*$",
        re.IGNORECASE,
    )
    _APPROVE_SESSION_RE = re.compile(
        r"^\s*(?:aprovar|approve|sim,?\s*aprovar|pode\s+executar|pode\s+seguir|autorizo|liberar\s+esta\s+a[cç][aã]o)\s*$",
        re.IGNORECASE,
    )
    _APPROVE_LAST_RE = re.compile(
        r"^\s*(?:aprovar|approve)\s+(?:ultima|última|ultima\s+a[cç][aã]o|última\s+a[cç][aã]o|last)\s*$",
        re.IGNORECASE,
    )
    _DENY_SESSION_RE = re.compile(
        r"^\s*(?:negar|rejeitar|deny|reject|cancelar|cancel|n[aã]o\s+aprovar|bloquear|n[aã]o\s+execute)\s*$",
        re.IGNORECASE,
    )
    _DETAILS_RE = re.compile(
        rf"^\s*mostrar\s+(?P<detail>preview|riscos?|policy|diff|comando|arquivos\s+afetados)(?:\s+(?P<target>{_APPROVAL_ID}))?\s*$",
        re.IGNORECASE,
    )
    _SCOPE_RE = re.compile(
        r"^\s*permitir\s+(?P<scope>s[oó]\s+leitura|s[oó]\s+este\s+arquivo|s[oó]\s+este\s+comando|s[oó]\s+este\s+workspace|s[oó]\s+esta\s+vez)\s*$",
        re.IGNORECASE,
    )
    _TASK_BATCH_RE = re.compile(
        r"^\s*(?P<action>aprovar\s+(?:todas|todos)|approve\s+all|negar\s+(?:todas|todos)|deny\s+all|reject\s+all)\s+"
        r"(?P<target>(?:task_run|task)_[A-Za-z0-9_-]+)\s*$",
        re.IGNORECASE,
    )
    _LIST_RE = re.compile(
        r"^\s*(?:listar|liste|mostrar|mostre|list|show)\s+(?:approvals|aprovacoes|aprova[cç][oõ]es)(?:\s+(?P<scope>pendentes|pending))?\s*$",
        re.IGNORECASE,
    )

    _APPROVE_SESSION_RE = re.compile(
        r"^\s*(?:aprovar|approve|sim,?\s*aprovar|pode\s+executar|pode\s+seguir|pode\s+implementar|"
        r"autorizo|esta\s+aprovado|est[aá]\s+aprovado|permiss[aã]o\s+concedida|"
        r"j[aá]\s+cliquei\s+em\s+permitir|liberar\s+esta\s+acao|liberar\s+esta\s+a[cç][aă]o)\s*$",
        re.IGNORECASE,
    )
    _TASK_APPROVAL_RE = re.compile(
        r"^\s*(?P<action>aprovar|approve|negar|rejeitar|deny|reject|cancelar|cancel)\s+"
        r"(?P<target>(?:task_run|task)_[A-Za-z0-9_-]+)\s*$",
        re.IGNORECASE,
    )
    _LIST_RE = re.compile(
        r"^\s*(?:listar|liste|mostrar|mostre|list|show)\s+(?:approvals|aprovacoes|aprova[cç][oő]es)"
        r"(?:\s+(?P<scope>pendentes|pending|todos|all))?\s*$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        approvals: ApprovalService | None = None,
        continuation: ApprovalTaskContinuationService | None = None,
        grants: SessionGrantService | None = None,
    ) -> None:
        self.approvals = approvals or ApprovalService()
        self.continuation = continuation or ApprovalTaskContinuationService(approvals=self.approvals)
        self.grants = grants or SessionGrantService()

    def parse(self, text: str) -> ApprovalCommand | None:
        list_match = self._LIST_RE.match(text or "")
        if list_match:
            raw_scope = (list_match.group("scope") or "").casefold()
            return ApprovalCommand(
                action="list",
                target_id=None,
                target_kind="approval",
                scope="pending" if raw_scope in {"pendentes", "pending"} else "all",
                source_text=text,
            )
        grant_match = self._GRANT_RE.match(text or "")
        if grant_match:
            raw_action = grant_match.group("action").casefold()
            return ApprovalCommand(
                action=self._normalized_action(raw_action),
                target_id=grant_match.group("target"),
                target_kind="grant",
                scope="single_action",
                source_text=text,
            )
        approval_match = self._APPROVAL_RE.match(text or "")
        if approval_match:
            raw_action = approval_match.group("action").casefold()
            return ApprovalCommand(
                action=self._normalized_action(raw_action),
                target_id=approval_match.group("target"),
                target_kind="approval",
                scope="single_action",
                strong_action=self._normalized_strong_action(approval_match.group("strong") or ""),
                source_text=text,
            )
        detail_match = self._DETAILS_RE.match(text or "")
        if detail_match:
            return ApprovalCommand(
                action="show_details",
                target_id=detail_match.group("target"),
                target_kind="approval" if detail_match.group("target") else "session",
                scope="single_action",
                detail_type=self._normalized_detail(detail_match.group("detail")),
                source_text=text,
            )
        scope_match = self._SCOPE_RE.match(text or "")
        if scope_match:
            return ApprovalCommand(
                action="scope_change",
                target_id=None,
                target_kind="session",
                scope=self._normalized_scope(scope_match.group("scope")),
                source_text=text,
            )
        if self._APPROVE_LAST_RE.match(text or ""):
            return ApprovalCommand(action="approve", target_id=None, target_kind="session", scope="last_action", source_text=text)
        if self._APPROVE_SESSION_RE.match(text or ""):
            return ApprovalCommand(action="approve", target_id=None, target_kind="session", scope="single_pending", source_text=text)
        if self._DENY_SESSION_RE.match(text or ""):
            return ApprovalCommand(action="deny", target_id=None, target_kind="session", scope="single_pending", source_text=text)
        task_match = self._TASK_BATCH_RE.match(text or "")
        if task_match:
            raw_action = task_match.group("action").casefold()
            return ApprovalCommand(
                action="approve" if "aprovar" in raw_action or "approve" in raw_action else "deny",
                target_id=task_match.group("target"),
                target_kind="task",
                scope="safe_batch",
                source_text=text,
            )
        task_single_match = self._TASK_APPROVAL_RE.match(text or "")
        if task_single_match:
            raw_action = task_single_match.group("action").casefold()
            return ApprovalCommand(
                action=self._normalized_action(raw_action),
                target_id=task_single_match.group("target"),
                target_kind="task",
                scope="single_pending",
                source_text=text,
            )
        return None

    def handle(self, session_id: str, text: str, *, source_channel: str = "api", message_id: str | None = None) -> ChatResponse | None:
        command = self.parse(text)
        if command is None:
            return None
        try:
            if command.action == "list":
                payload = self._execute(command, session_id=session_id, source_channel=source_channel, message_id=message_id)
                return self._response(session_id, command, payload)
            if command.target_kind == "grant":
                payload = self._execute_grant(command, session_id=session_id, source_channel=source_channel, message_id=message_id)
                return self._grant_response(session_id, command, payload)
            payload = self._execute(command, session_id=session_id, source_channel=source_channel, message_id=message_id)
            return self._response(session_id, command, payload)
        except ValueError as exc:
            return ChatResponse(
                response_id=f"approval_cmd_{command.target_id or 'session'}",
                session_id=session_id,
                status="blocked",
                message=(
                    "Nao consegui executar esse comando de approval. "
                    f"Motivo: {str(exc)}. Use um approval_id pendente ou um task_id com approvals seguros."
                ),
                intent={"intent_type": "approval_command", "requires_task": False},
                policy={"approval_command": True, "reason_code": str(exc)},
                operation_type="approval_command",
                message_type="blocked_policy_message",
                requires_user_action=True,
                is_final_answer=False,
                grounded=True,
                warnings=[str(exc)],
            )

    def _execute_grant(self, command: ApprovalCommand, *, session_id: str, source_channel: str, message_id: str | None) -> dict[str, Any]:
        if not command.target_id:
            raise ValueError("grant_id_required")
        if command.action == "approve":
            decision = self.grants.approve(command.target_id, actor=f"chat_command:{source_channel}")
        elif command.action in {"deny", "cancel"}:
            decision = self.grants.deny(command.target_id, actor=f"chat_command:{source_channel}")
        else:
            raise ValueError("unsupported_grant_command")
        return {
            "status": decision.status,
            "reason_code": decision.reason_code,
            "grant": decision.grant.model_dump(),
            "source_channel": source_channel,
            "message_id": message_id,
        }

    def _grant_response(self, session_id: str, command: ApprovalCommand, payload: dict[str, Any]) -> ChatResponse:
        grant = payload.get("grant") if isinstance(payload.get("grant"), dict) else {}
        grant_id = str(grant.get("grant_id") or command.target_id or "")
        status = str(payload.get("status") or "")
        reason_code = str(payload.get("reason_code") or "")
        ok = status == "approved"
        denied = status == "denied"
        message = (
            f"Permissao temporaria aprovada: {grant_id}. "
            "Ela continua limitada ao escopo registrado e nao altera a policy permanente."
            if ok
            else (
                f"Permissao temporaria negada: {grant_id}."
                if denied
                else f"Nao consegui aplicar a decisao do grant {grant_id}. Motivo: {reason_code}."
            )
        )
        return ChatResponse(
            response_id=f"grant_cmd_{grant_id or 'unknown'}",
            session_id=session_id,
            status="ok" if ok or denied else "blocked",
            message=message,
            intent={"intent_type": "session_grant_command", "requires_task": False},
            policy={"grant_command": True, "reason_code": reason_code, "grant_status": status},
            contract_preview={"grant": grant},
            operation_type="session_grant_command",
            message_type="assistant_final_answer" if ok or denied else "blocked_policy_message",
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            warnings=[] if ok or denied else [reason_code],
        )

    def _execute(self, command: ApprovalCommand, *, session_id: str, source_channel: str, message_id: str | None) -> dict[str, Any]:
        actor = Actor(type="user", id=f"chat_command:{source_channel}")
        if command.action == "list":
            status_filter = "pending" if command.scope == "pending" else None
            approvals = self.approvals.list_approvals(status=status_filter, session_id=session_id, limit=100)
            if not approvals and session_id:
                approvals = self.approvals.list_approvals(status=status_filter, limit=100)
            return {
                "status": "approval_list",
                "scope": command.scope,
                "approvals": [approval.model_dump() for approval in approvals],
                "source_channel": source_channel,
                "message_id": message_id,
            }
        if command.action == "scope_change":
            return {
                "status": "scope_change_previewed",
                "source_channel": source_channel,
                "message_id": message_id,
                "message": (
                    "Alteracao de escopo detectada. Isso nao altera policy automaticamente; "
                    "precisa virar ConfigChangeRequest/ApprovalRequest antes de aplicar."
                ),
                "scope": command.scope,
            }
        if command.action == "show_details":
            approval = self._resolve_approval(command, session_id=session_id, allow_last=True)
            self.approvals.append_event(
                approval.approval_id,
                f"approval_{command.detail_type or 'preview'}_requested_from_chat",
                "Detalhes do ApprovalRequest solicitados pelo chat.",
                {"source_channel": source_channel, "message_id": message_id, "decision_text": command.source_text},
            )
            return {"status": "details", "approval": approval.model_dump(), "detail_type": command.detail_type or "preview"}
        if command.target_kind == "task":
            if command.scope == "single_pending":
                pending_for_task = self.approvals.list_for_task(command.target_id or "", status="pending", limit=500)
                if not pending_for_task:
                    return {
                        "status": "blocked",
                        "reason_code": "no_pending_approval_for_task",
                        "task_id": command.target_id,
                        "approvals": [],
                        "message": "NENHUM_APPROVAL_PENDENTE_PARA_TASK",
                    }
                if len(pending_for_task) > 1:
                    return {
                        "status": "blocked",
                        "reason_code": "approval_ambiguous_for_task",
                        "task_id": command.target_id,
                        "approvals": [approval.model_dump() for approval in pending_for_task[:20]],
                        "message": "APPROVAL_AMBIGUO",
                    }
                approval = pending_for_task[0]
                if command.action == "approve":
                    refreshed = self.approvals.refresh_policy(approval.approval_id)
                    if refreshed is not None and refreshed.status != "pending":
                        raise ValueError("approval_preview_hash_mismatch_or_policy_changed")
                    decision, approval = self.approvals.approve(
                        approval.approval_id,
                        actor=actor,
                        reason="chat_approval_command_for_task",
                        scope=command.scope,
                    )
                    resume = self.continuation.after_decision(approval, auto_process=True)
                elif command.action == "cancel":
                    decision, approval = self.approvals.cancel(
                        approval.approval_id,
                        actor=actor,
                        reason="chat_cancel_approval_command_for_task",
                        scope=command.scope,
                    )
                    resume = self.continuation.after_decision(approval, auto_process=False)
                else:
                    decision, approval = self.approvals.reject(
                        approval.approval_id,
                        actor=actor,
                        reason="chat_deny_approval_command_for_task",
                        scope=command.scope,
                    )
                    resume = self.continuation.after_decision(approval, auto_process=False)
                return {
                    "status": "ok",
                    "task_id": command.target_id,
                    "approval": approval.model_dump(),
                    "approvals": [approval.model_dump()],
                    "decision": decision.model_dump(),
                    "decisions": [decision.model_dump()],
                    "resume": resume,
                    "resume_results": [resume],
                }
            if command.action == "approve":
                return self.continuation.approve_safe_batch_for_task(
                    command.target_id or "",
                    actor=actor,
                    reason="chat_safe_batch_approval_command",
                )
            decisions = self.approvals.reject_batch(
                [approval.approval_id for approval in self.approvals.list_for_task(command.target_id or "", status="pending", limit=500)],
                actor=actor,
                reason="chat_batch_deny_command",
                safe_only=False,
            )
            resume_results = [
                self.continuation.after_decision(approval, auto_process=False)
                for _decision, approval in decisions
            ]
            return {
                "status": "ok",
                "task_id": command.target_id,
                "approvals": [approval.model_dump() for _decision, approval in decisions],
                "decisions": [decision.model_dump() for decision, _approval in decisions],
                "resume_results": resume_results,
                "queue_process": self.continuation._process_queue_if_enabled(),
            }
        approval = self._resolve_approval(command, session_id=session_id, allow_last=command.scope == "last_action")
        self.approvals.append_event(
            approval.approval_id,
            "chat_approval_command_detected",
            "Comando textual de approval detectado no chat.",
            {
                "source_channel": source_channel,
                "session_id": session_id,
                "message_id": message_id,
                "approval_id": approval.approval_id,
                "decision_text": command.source_text,
                "decision_actor": actor.model_dump(),
                "scope": command.scope,
            },
        )
        self._enforce_specific_approval_phrase(command, approval)
        if command.action == "approve":
            refreshed = self.approvals.refresh_policy(approval.approval_id)
            if refreshed is not None and refreshed.status != "pending":
                raise ValueError("approval_preview_hash_mismatch_or_policy_changed")
            decision, approval = self.approvals.approve(
                approval.approval_id,
                actor=actor,
                reason="chat_approval_command",
                scope=command.scope,
            )
        elif command.action == "cancel":
            decision, approval = self.approvals.cancel(
                approval.approval_id,
                actor=actor,
                reason="chat_cancel_approval_command",
                scope=command.scope,
            )
        else:
            decision, approval = self.approvals.reject(
                approval.approval_id,
                actor=actor,
                reason="chat_deny_approval_command",
                scope=command.scope,
            )
        self.approvals.append_event(
            approval.approval_id,
            "approval_decision_received_from_chat",
            "Decisao de approval recebida pelo chat.",
            {
                "source_channel": source_channel,
                "session_id": session_id,
                "message_id": message_id,
                "approval_id": approval.approval_id,
                "decision_text": command.source_text,
                "status": approval.status,
            },
        )
        return {
            "status": "ok",
            "approval": approval.model_dump(),
            "decision": decision.model_dump(),
            "resume": self.continuation.after_decision(approval),
        }

    def _response(self, session_id: str, command: ApprovalCommand, payload: dict[str, Any]) -> ChatResponse:
        status = str(payload.get("status") or "ok")
        if status == "details":
            approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
            detail_type = str(payload.get("detail_type") or "preview")
            message = self._details_message(approval, detail_type)
            target_id = str(approval.get("approval_id") or command.target_id or "approval")
            return ChatResponse(
                response_id=f"approval_details_{target_id}",
                session_id=session_id,
                status="ok",
                message=message,
                intent={"intent_type": "approval_command", "detail_type": detail_type},
                policy={"approval_command": True, "details_only": True},
                operation_type="approval_command",
                operation_id=f"approval_details_{target_id}",
                message_type="task_status_update",
                approval_id=target_id,
                requires_user_action=True,
                is_final_answer=False,
                grounded=True,
                evidence_refs=[{"type": "approval_request", "ref_id": target_id}],
                contract_preview=payload,
            )
        if status == "scope_change_previewed":
            return ChatResponse(
                response_id="approval_scope_change_previewed",
                session_id=session_id,
                status="preview",
                message=str(payload.get("message")),
                intent={"intent_type": "approval_scope_change", "scope": payload.get("scope")},
                policy={"approval_command": True, "requires_config_change_request": True},
                operation_type="approval_scope_change",
                message_type="task_preview",
                requires_user_action=True,
                is_final_answer=False,
                grounded=True,
                contract_preview=payload,
            )
        if status == "approval_list":
            approvals = payload.get("approvals") if isinstance(payload.get("approvals"), list) else []
            lines = []
            for approval in approvals[:20]:
                if not isinstance(approval, dict):
                    continue
                lines.append(
                    "- "
                    f"{approval.get('approval_id')} | status={approval.get('status')} | "
                    f"preview={approval.get('preview_id') or 'n/a'} | "
                    f"draft={approval.get('draft_id') or 'n/a'} | "
                    f"task={approval.get('task_id') or 'n/a'} | "
                    f"operation={approval.get('operation_type') or 'n/a'} | "
                    f"contract={approval.get('contract_type') or 'n/a'} | "
                    f"runtime={approval.get('runtime_profile') or 'n/a'} | "
                    f"acao={','.join(str(item) for item in approval.get('actions_requested', []) or []) or 'n/a'} | "
                    f"workspace={approval.get('workspace_path') or approval.get('workspace_id') or 'n/a'} | "
                    f"arquivos={','.join(str(item) for item in approval.get('target_paths', []) or []) or 'n/a'} | "
                    f"plan={approval.get('executable_plan_ref') or 'n/a'} | "
                    f"resume={approval.get('resume_status') or 'n/a'} | "
                    f"block={approval.get('block_reason_code') or 'n/a'} | "
                    f"comando={','.join(str(item) for item in approval.get('commands', []) or []) or 'n/a'} | "
                    f"aprovar=APROVAR {approval.get('approval_id')}"
                )
            message = (
                "APPROVALS PENDENTES\n\n" if command.scope == "pending" else "APPROVALS\n\n"
            ) + ("\n".join(lines) if lines else "NENHUM_APPROVAL_PENDENTE")
            return ChatResponse(
                response_id=f"approval_list_{session_id}",
                session_id=session_id,
                status="ok",
                message=message,
                intent={"intent_type": "approval_command", "target_kind": "approval", "scope": command.scope},
                policy={"approval_command": True, "listed_count": len(approvals)},
                operation_type="approval_command",
                operation_id=f"approval_list_{session_id}",
                message_type="task_status_update",
                requires_user_action=bool(approvals),
                is_final_answer=False,
                grounded=True,
                contract_preview={"approvals": approvals},
                next_actions=[
                    ChatNextAction(type="review_approval", label="Revisar approval", target_id=str(approval.get("approval_id")))
                    for approval in approvals[:5]
                    if isinstance(approval, dict) and approval.get("approval_id")
                ],
            )
        approved = command.action == "approve"
        denied = command.action in {"deny", "cancel"}
        approval_payload = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
        approval_ref = str(approval_payload.get("approval_id") or "")
        target = approval_ref or command.target_id or "session"
        resume = self._primary_resume(payload)
        resume_problem = self._resume_problem_status(resume)
        if approved and status == "ok" and resume_problem:
            status = resume_problem
            task_run_id = resume.get("task_run_id") or resume.get("run_id") or resume.get("task_id") or "n/a"
            block_reason = (
                resume.get("block_reason_code")
                or resume.get("reason_code")
                or resume.get("failure_reason_code")
                or resume.get("missing_plan")
                or f"task_run_{resume_problem}_after_approval"
            )
            failed_step = resume.get("failed_step_id") or resume.get("blocked_step") or "n/a"
            heading = (
                "APPROVAL_REGISTERED_BUT_TASK_FAILED"
                if resume_problem == "failed"
                else "APPROVAL_REGISTERED_BUT_TASK_BLOCKED"
            )
            next_action = (
                "diagnosticar a falha do TaskRun e criar novo preview de recuperacao governada."
                if resume_problem == "failed"
                else "recriar TaskDraft com plano executavel antes de aprovar."
            )
            message = (
                f"{heading}\n\n"
                f"approval_id: {target}\n"
                f"task_run_id: {task_run_id}\n"
                f"task_status: {resume_problem}\n"
                f"failed_step: {failed_step}\n"
                f"block_reason_code: {block_reason}\n"
                "files_written: false\n"
                f"next_action: {next_action}"
            )
        elif approved and status == "ok":
            message = (
                "Approval registrado. A task foi liberada para continuar pela fila governada; "
                "as policies, capabilities e validacoes continuam ativas."
            )
        elif denied:
            message = "Approval encerrado. A acao nao sera executada e a task sera reconciliada pelo runtime."
        else:
            message = f"Comando de approval processado com status {status}."
        return ChatResponse(
            response_id=f"approval_cmd_{target}",
            session_id=session_id,
            status=(
                "ok"
                if status == "ok"
                else "failed"
                if status == "failed"
                else "blocked"
                if status in {"blocked", "cancelled", "expired"}
                else "degraded"
            ),
            message=message,
            intent={"intent_type": "approval_command", "target_kind": command.target_kind, "scope": command.scope},
            policy={"governed_runtime_resume": True, "blanket_approval": False},
            operation_type="approval_command",
            operation_id=f"approval_cmd_{target}",
            message_type="task_status_update",
            approval_id=target if target.startswith("approval_") else None,
            task_id=command.target_id if command.target_kind == "task" else None,
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            evidence_refs=[{"type": "approval_command_result", "ref_id": target}],
            next_actions=[
                ChatNextAction(type="open_pipeline", label="Ver pipeline", target_id=target),
            ],
            contract_preview=payload,
        )

    @staticmethod
    def _primary_resume(payload: dict[str, Any]) -> dict[str, Any]:
        resume = payload.get("resume")
        if isinstance(resume, dict):
            return resume
        resume_results = payload.get("resume_results")
        if isinstance(resume_results, list):
            for item in resume_results:
                if isinstance(item, dict):
                    return item
        return {}

    @staticmethod
    def _resume_problem_status(resume: dict[str, Any]) -> str | None:
        status_values = {
            str(resume.get("status") or "").casefold(),
            str(resume.get("run_status") or "").casefold(),
            str(resume.get("task_status") or "").casefold(),
        }
        if "failed" in status_values:
            return "failed"
        if "blocked" in status_values:
            return "blocked"
        if "cancelled" in status_values:
            return "cancelled"
        if "expired" in status_values:
            return "expired"
        reason = str(resume.get("reason_code") or resume.get("block_reason_code") or "").casefold()
        if reason and reason not in {"ok", "none", "queued", "started"}:
            return "blocked"
        return None

    def _resolve_approval(self, command: ApprovalCommand, *, session_id: str, allow_last: bool) -> Any:
        if command.target_id:
            approval = self.approvals.get_approval(command.target_id)
            if approval is None:
                raise ValueError("approval_not_found")
            return approval
        pending = self.approvals.list_approvals(status="pending", session_id=session_id, limit=500)
        if not pending:
            raise ValueError("approval_not_found")
        if allow_last:
            return sorted(pending, key=lambda item: item.created_at or item.updated_at, reverse=True)[0]
        if len(pending) != 1:
            for approval in pending[:20]:
                self.approvals.append_event(
                    approval.approval_id,
                    "approval_ambiguous_decision",
                    "Comando textual sem approval_id encontrou multiplas pendencias.",
                    {"session_id": session_id, "pending_count": len(pending)},
                )
            raise ValueError("approval_ambiguous_decision")
        return pending[0]

    def _enforce_specific_approval_phrase(self, command: ApprovalCommand, approval: Any) -> None:
        if command.action != "approve":
            return
        dangerous = self._dangerous_actions(set(str(item) for item in approval.actions_requested))
        if not dangerous:
            return
        required = dangerous[0]
        if command.strong_action != required:
            raise ValueError(f"specific_approval_phrase_required:{required}")

    @staticmethod
    def _dangerous_actions(actions: set[str]) -> list[str]:
        result: list[str] = []
        if actions.intersection({"delete_file", "delete_files"}):
            result.append("delete")
        if actions.intersection({"move_file", "move_files"}):
            result.append("move")
        if "git_push" in actions:
            result.append("git_push")
        return result

    @staticmethod
    def _details_message(approval: dict[str, Any], detail_type: str) -> str:
        approval_id = str(approval.get("approval_id") or "")
        action = ", ".join(str(item) for item in approval.get("actions_requested", []) or [])
        risk = str(approval.get("risk_level") or "unknown")
        workspace = str(approval.get("workspace_path") or approval.get("workspace_id") or "workspace nao informado")
        target_paths = ", ".join(str(item) for item in approval.get("target_paths", []) or []) or "sem arquivos alvo"
        commands = ", ".join(str(item) for item in approval.get("commands", []) or []) or "sem comando"
        preview = approval.get("preview") if isinstance(approval.get("preview"), dict) else {}
        preview_summary = str(preview.get("summary") or preview.get("content_preview_ref") or "preview disponivel no ApprovalRequest")
        if detail_type == "command":
            body = f"Comando: {commands}"
        elif detail_type == "files":
            body = f"Arquivos afetados: {target_paths}"
        elif detail_type == "risks":
            body = f"Risco: {risk}. Acoes: {action or 'nao informado'}."
        elif detail_type == "policy":
            body = f"Policy: approval_required. Acoes pedidas: {action or 'nao informado'}."
        else:
            body = f"Preview: {preview_summary}"
        return (
            "APPROVAL DETAILS\n\n"
            f"approval_id: {approval_id}\n"
            f"workspace: {workspace}\n"
            f"{body}\n\n"
            f"Para aprovar: APROVAR {approval_id}\n"
            f"Para negar: NEGAR {approval_id}"
        )

    @staticmethod
    def _normalized_action(value: str) -> str:
        if value in {"aprovar", "aprove", "approve"}:
            return "approve"
        if value in {"cancelar", "cancel"}:
            return "cancel"
        return "deny"

    @staticmethod
    def _normalized_strong_action(value: str) -> str | None:
        normalized = " ".join((value or "").casefold().split())
        if normalized in {"delete", "deletar"}:
            return "delete"
        if normalized in {"move", "mover"}:
            return "move"
        if normalized == "git push":
            return "git_push"
        return None

    @staticmethod
    def _normalized_detail(value: str) -> str:
        normalized = " ".join(value.casefold().split())
        if normalized.startswith("risco"):
            return "risks"
        if normalized == "comando":
            return "command"
        if normalized == "arquivos afetados":
            return "files"
        return normalized

    @staticmethod
    def _normalized_scope(value: str) -> str:
        normalized = " ".join(value.casefold().split())
        replacements = {
            "so leitura": "read_only",
            "só leitura": "read_only",
            "so este arquivo": "single_file",
            "só este arquivo": "single_file",
            "so este comando": "single_command",
            "só este comando": "single_command",
            "so este workspace": "single_workspace",
            "só este workspace": "single_workspace",
            "so esta vez": "single_use",
            "só esta vez": "single_use",
        }
        return replacements.get(normalized, normalized.replace(" ", "_"))
