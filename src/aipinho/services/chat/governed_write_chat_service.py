from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentRunUpdateRequest, AgentSessionCreateRequest
from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.schemas.governed_write import GovernedWriteOutcome, GovernedWriteRequest
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.core.paths import PATHS
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file


class GovernedWriteChatService:
    """Routes explicit chat write requests through the governed Tool Gateway."""

    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        workspace_resolver: AgentToolWorkspaceResolver | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
        planner: AgentLocalActionPlanner | None = None,
        require_chat_write_approval: bool | None = None,
        draft_store: TaskDraftStore | None = None,
        preview_service: TaskPreviewService | None = None,
        approval_service: ApprovalService | None = None,
    ) -> None:
        self.tool_gateway = tool_gateway
        self.kernel = kernel or (tool_gateway.kernel if tool_gateway is not None else AgentSessionKernelService())
        self.workspace_resolver = workspace_resolver or (tool_gateway.resolver if tool_gateway is not None else AgentToolWorkspaceResolver())
        self.planner = planner or AgentLocalActionPlanner()
        self.require_chat_write_approval = require_chat_write_approval
        self.draft_store = draft_store or TaskDraftStore()
        self.preview_service = preview_service or TaskPreviewService(draft_store=self.draft_store)
        self.approval_service = approval_service or ApprovalService(preview_service=self.preview_service, draft_store=self.draft_store)

    def from_decision(
        self,
        *,
        session_id: str,
        prompt: str,
        decision: ChatOperationDecision,
        workspace_ref: str | None,
        requested_capabilities: list[str] | None = None,
        execution_mode: str = "governed_autorun",
    ) -> ChatResponse | None:
        router_operation = str(decision.metadata.get("router_operation_type") or "")
        requested_operation = str(decision.metadata.get("requested_operation") or "")
        is_governed_write = router_operation == "governed_file_write" or (
            decision.operation_type in {"filesystem_write_file", "filesystem_modify_file"}
            and requested_operation in {"create_file", "modify_file"}
            and bool(decision.metadata.get("workspace_write"))
        )
        if not is_governed_write:
            return None
        negative_constraints = self._negative_constraint_flags(prompt, decision)
        if negative_constraints["write_allowed"] is False:
            outcome = GovernedWriteOutcome(
                status="blocked",
                reason_code="negative_write_constraint",
                workspace_ref=workspace_ref or decision.workspace,
                warnings=["negative_write_constraint", *negative_constraints["matched_constraints"]],
                evidence_refs=[
                    {
                        "type": "intent_contract",
                        "ref_id": decision.operation_id,
                        "human_label": "Negative constraints",
                    }
                ],
            )
            response = self.to_chat_response(session_id=session_id, decision=decision, outcome=outcome)
            return response.model_copy(
                update={
                    "message": (
                        "Nao executei escrita porque o pedido contem restricoes explicitas de leitura/chat-only. "
                        "A operacao correta e responder no chat ou usar uma rota read-only."
                    ),
                    "intent": {
                        **response.intent,
                        "write_allowed": False,
                        "shell_allowed": negative_constraints["shell_allowed"],
                        "report_file_allowed": negative_constraints["report_file_allowed"],
                        "chat_only": negative_constraints["chat_only"],
                        "readonly": negative_constraints["readonly"],
                    },
                    "policy": {
                        **response.policy,
                        "workspace_write": False,
                        "negative_constraints": negative_constraints,
                    },
                }
            )
        requested_operation = requested_operation or "create_file"
        write_capability = "modify_file" if requested_operation == "modify_file" else "create_file"
        target_resolution = str(decision.metadata.get("target_resolution") or "")
        request = GovernedWriteRequest(
            operation_type=write_capability,  # type: ignore[arg-type]
            session_id=session_id,
            prompt=prompt,
            workspace_ref=(workspace_ref or decision.workspace or "").strip() or None,
            filename=self.planner.extract_requested_filename(prompt),
            content_hint=self.planner.extract_requested_content(prompt) or "",
            requested_capabilities=list(dict.fromkeys([*(requested_capabilities or []), "read_workspace", write_capability, "workspace_write"])),
            execution_mode=execution_mode,
            metadata_sanitized={"operation_id": decision.operation_id, "operation_type": decision.operation_type, "target_resolution": target_resolution},
        )
        outcome = self.execute(request)
        return self.to_chat_response(session_id=session_id, decision=decision, outcome=outcome)

    def execute(self, request: GovernedWriteRequest) -> GovernedWriteOutcome:
        allow_inferred_target = request.operation_type == "modify_file" and request.metadata_sanitized.get("target_resolution") == "infer_ui_source"
        if not request.filename and not allow_inferred_target:
            return GovernedWriteOutcome(status="needs_clarification", reason_code="target_filename_missing", workspace_ref=request.workspace_ref, warnings=["target_filename_missing"])
        if not request.workspace_ref:
            return GovernedWriteOutcome(status="needs_clarification", reason_code="target_workspace_missing", warnings=["target_workspace_missing"])

        workspace = self._resolve_workspace(request.workspace_ref)
        if not workspace.allowed:
            status = "needs_clarification" if workspace.reason_code in {"workspace_unknown", "workspace_id_not_registered"} else "blocked"
            return GovernedWriteOutcome(
                status=status,
                reason_code=workspace.reason_code,
                workspace_ref=request.workspace_ref,
                workspace_id=workspace.workspace_id,
                workspace_role=workspace.workspace_role,
                resolved_path_sanitized=workspace.resolved_path_sanitized or workspace.root_path_sanitized,
                evidence_refs=[{"type": "workspace_policy", "ref_id": workspace.workspace_id or "workspace_resolution", "human_label": "Workspace Tool Gateway"}],
                warnings=[workspace.reason_code],
            )

        if self._chat_write_requires_approval(request, workspace):
            approval_context = self._create_approval_request(request, workspace)
            return GovernedWriteOutcome(
                status="approval_required",
                reason_code="approval_required_before_workspace_write",
                workspace_ref=request.workspace_ref,
                workspace_id=workspace.workspace_id,
                workspace_role=workspace.workspace_role,
                resolved_path_sanitized=workspace.resolved_path_sanitized or workspace.root_path_sanitized,
                draft_id=approval_context["draft_id"],
                preview_id=approval_context["preview_id"],
                approval_id=approval_context["approval_id"],
                warnings=["approval_required_before_workspace_write"],
                evidence_refs=[
                    {"type": "workspace_policy", "ref_id": workspace.workspace_id or "workspace_resolution", "human_label": "Workspace Tool Gateway"},
                    {"type": "approval_policy", "ref_id": "require_human_approval_for_chat_workspace_write", "human_label": "Chat workspace write approval guard"},
                    {"type": "task_draft", "ref_id": approval_context["draft_id"], "human_label": "Draft de escrita governada"},
                    {"type": "task_preview", "ref_id": approval_context["preview_id"], "human_label": "Preview de escrita governada"},
                    {"type": "approval_request", "ref_id": approval_context["approval_id"], "human_label": "Approval de escrita governada"},
                ],
            )

        agent_session = self.kernel.create_session(
            "aipinho",
            AgentSessionCreateRequest(
                title="AIpinho Chat governed write",
                active_workspace_id=workspace.workspace_id,
                metadata_sanitized={"chat_session_id": request.session_id, "operation_type": request.operation_type, **request.metadata_sanitized},
            ),
        )
        run = self.kernel.create_run(
            "aipinho",
            agent_session.session_id,
            AgentRunCreateRequest(
                operation_type=request.operation_type,
                status="running",
                workspace_id=workspace.workspace_id,
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={"chat_session_id": request.session_id, **request.metadata_sanitized},
            ),
        )
        gateway = self.tool_gateway or AgentToolGatewayService(kernel=self.kernel)
        planner = AgentLocalActionPlanner(gateway)
        planner_kwargs = {
            "agent_id": "aipinho",
            "run_id": run.run_id,
            "prompt": request.prompt,
            "workspace_context": workspace.resolved_path_sanitized or workspace.root_path_sanitized,
            "requested_capabilities": request.requested_capabilities,
            "content_hint": request.content_hint,
            "execution_mode": request.execution_mode,
            "metadata_sanitized": {"chat_session_id": request.session_id, **request.metadata_sanitized},
        }
        if allow_inferred_target:
            result = planner.run_inferred_ui_text_update(**planner_kwargs)
        else:
            result = (
                planner.run_explicit_modify_file(**planner_kwargs)
                if request.operation_type == "modify_file"
                else planner.run_explicit_create_file(**planner_kwargs)
            )
        if result is None:
            self.kernel.update_run(run.run_id, AgentRunUpdateRequest(status="cancelled", metadata_sanitized={"reason": "no_explicit_create_file_request"}))
            return GovernedWriteOutcome(
                status="needs_clarification",
                reason_code="explicit_create_file_request_not_resolved",
                workspace_id=workspace.workspace_id,
                workspace_role=workspace.workspace_role,
                resolved_path_sanitized=workspace.resolved_path_sanitized,
                run_id=run.run_id,
                warnings=["explicit_create_file_request_not_resolved"],
            )

        validation_status = result.validation_result.status if result.validation_result else None
        validation_failed = result.status == "succeeded" and validation_status not in {None, "passed"}
        final_status = "failed" if validation_failed else ("completed" if result.status == "succeeded" else ("pending_approval" if result.status == "approval_required" else ("failed" if result.status == "failed" else "blocked")))
        reason_code = result.tool_invocation.block_reason_code or result.tool_invocation.error_code or (result.policy_decision.reason_code if result.policy_decision else None)
        if validation_failed and not reason_code:
            reason_code = "operation_failed_validation"
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status=final_status,
                validation_status=validation_status,
                error_code=reason_code if result.status != "succeeded" or validation_failed else None,
                metadata_sanitized={
                    "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                    "policy_decision_id": result.policy_decision.policy_decision_id if result.policy_decision else None,
                },
            ),
        )
        evidence_refs = [
            {"type": "agent_run", "ref_id": run.run_id, "human_label": "Run governado AIpinho"},
            {"type": "tool_invocation", "ref_id": result.tool_invocation.tool_invocation_id, "human_label": f"Tool Gateway {request.operation_type}"},
        ]
        return GovernedWriteOutcome(
            status="failed" if validation_failed else result.status,
            reason_code=reason_code,
            workspace_ref=request.workspace_ref,
            workspace_id=result.tool_invocation.workspace_id or workspace.workspace_id,
            workspace_role=result.tool_invocation.workspace_role or workspace.workspace_role,
            resolved_path_sanitized=workspace.resolved_path_sanitized,
            run_id=run.run_id,
            tool_invocation_id=result.tool_invocation.tool_invocation_id,
            policy_decision_id=result.policy_decision.policy_decision_id if result.policy_decision else None,
            validation_status=validation_status,
            file_path_sanitized=result.output.get("file_path_sanitized"),
            evidence_refs=evidence_refs,
            warnings=[reason_code] if reason_code and (result.status != "succeeded" or validation_failed) else [],
        )

    def _resolve_workspace(self, workspace_ref: str):
        by_id = self.workspace_resolver.resolve(workspace_id=workspace_ref, access="write")
        if by_id.allowed or by_id.reason_code != "workspace_id_not_registered":
            return by_id
        return self.workspace_resolver.resolve(path_ref=workspace_ref, access="write")

    def _create_approval_request(self, request: GovernedWriteRequest, workspace) -> dict[str, str]:
        now = utc_now()
        approval_action = "write_files"
        requested_operation = request.operation_type
        root = workspace.resolved_path_sanitized or workspace.root_path_sanitized or request.workspace_ref
        target_paths: list[str] = []
        if root and request.filename:
            try:
                target_paths.append(str((Path(root) / request.filename).resolve()))
            except OSError:
                target_paths.append(str(Path(root) / request.filename))
        elif root:
            target_paths.append(str(root))
        concrete_file_operations = [
            {
                "action": requested_operation,
                "target_path": target_paths[0],
                "content_source": "chat_prompt_or_content_hint",
                "validation": "file_exists",
            }
        ] if target_paths else []
        draft = TaskContractDraft(
            draft_id=f"chat_write_{uuid4().hex}",
            session_id=request.session_id,
            status="approval_required",
            intent_map={
                "operation": "governed_workspace_write",
                "requested_operation": requested_operation,
                "risk": "medium",
                "target_paths": target_paths,
                "target_path": target_paths[0] if target_paths else None,
                "concrete_file_operations": concrete_file_operations,
                "context_ref": f"chat_write_context:{request.metadata_sanitized.get('operation_id') or uuid4().hex}",
                "validation_plan": {
                    "checks": ["target_path_matches_preview", "filesystem_operation_recorded"],
                    "expected_outputs": ["filesystem_operation", "validation_result"],
                },
                "rollback_plan": {"strategy": "revert_or_delete_preview_targets", "target_paths": target_paths},
                "source_channel": "chat",
                "metadata": request.metadata_sanitized,
            },
            policy_decision={
                "decision_id": f"chat_write_policy_{uuid4().hex}",
                "status": "needs_approval",
                "allowed_actions": [],
                "denied_actions": [],
                "approval_required_for": [approval_action],
                "granted_capabilities": [],
                "denied_capabilities": [],
            },
            contract_type="filesystem_write",
            operation_type=requested_operation,
            intent_type="governed_file_write",
            runtime_profile="write_file",
            capabilities_required=list(dict.fromkeys([*request.requested_capabilities, "workspace_write"])),
            source_scope="chat",
            requires_workspace=True,
            workspace=TaskDraftWorkspace(path=root, status="confirmed" if root else "missing"),
            requested_actions=[approval_action],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=[approval_action],
            executable_plan_ref=f"chat_write_plan:{request.metadata_sanitized.get('operation_id') or uuid4().hex}",
            expected_outcomes=["filesystem_operation", "validation_result"],
            safe_to_execute=False,
            safe_to_preview=True,
            warnings=["approval_required_before_workspace_write"],
            trace=[
                {
                    "source": "services/chat/governed_write_chat_service.py",
                    "stage": "approval_bootstrap",
                    "decision": "approval_required",
                    "reason": "policy_ask_creates_approval_request_before_execution",
                    "operation_id": request.metadata_sanitized.get("operation_id"),
                    "requested_operation": requested_operation,
                }
            ],
            created_at=now,
            updated_at=now,
        )
        self.draft_store.save(draft)
        preview = self.preview_service.create_preview_from_draft(draft.draft_id)
        if preview is None or preview.status != "approval_required":
            raise RuntimeError("governed_write_preview_not_created")
        approval = self.approval_service.create_approval_for_preview(
            preview.preview_id,
            actions=[approval_action],
            reason="Chat requested governed workspace write approval",
        )
        self.approval_service.append_event(
            approval.approval_id,
            "approval_request_created",
            "Policy ask gerou ApprovalRequest antes de qualquer execucao.",
            {
                "source": "ask_policy_bootstrap",
                "session_id": request.session_id,
                "draft_id": draft.draft_id,
                "preview_id": preview.preview_id,
                "requested_operation": requested_operation,
                "target_paths": target_paths,
            },
        )
        return {"draft_id": draft.draft_id, "preview_id": preview.preview_id, "approval_id": approval.approval_id}

    def to_chat_response(self, *, session_id: str, decision: ChatOperationDecision, outcome: GovernedWriteOutcome) -> ChatResponse:
        public_operation_type = str(decision.metadata.get("router_operation_type") or decision.operation_type)
        intent = {
                "intent_type": public_operation_type,
                "requires_task": True,
                "requires_workspace": True,
                "output_target": "workspace_file",
                "requested_operation": decision.metadata.get("requested_operation", "create_file"),
            }
        policy = {
            "workspace_write": True,
            "tool_gateway": True,
            "reason_code": outcome.reason_code,
            "workspace_id": outcome.workspace_id,
            "workspace_role": outcome.workspace_role,
            "workspace_ref": outcome.workspace_ref,
            "workspace_path": outcome.resolved_path_sanitized,
            "file_path": outcome.file_path_sanitized,
            "validation_status": outcome.validation_status,
        }
        if outcome.status == "succeeded":
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                task_id=outcome.run_id,
                status="ok",
                message=(
                    "Conclui a escrita solicitada pelo fluxo governado.\n\n"
                    f"Arquivo: {outcome.file_path_sanitized or outcome.resolved_path_sanitized}\n"
                    f"Validacao: {outcome.validation_status or 'registrada'}"
                ),
                intent=intent,
                policy=policy,
                operation_id=decision.operation_id,
                operation_type=public_operation_type,
                message_type="assistant_final_answer",
                is_final_answer=True,
                grounded=True,
                evidence_refs=outcome.evidence_refs,
                warnings=outcome.warnings,
            )
        if outcome.status == "approval_required":
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                task_id=outcome.run_id,
                preview_id=outcome.preview_id,
                task_preview_id=outcome.preview_id,
                approval_id=outcome.approval_id,
                status="pending_approval",
                message=(
                    "APPROVAL_REQUIRED\n\n"
                    "A escrita foi identificada e eu criei o preview/approval antes de qualquer gravacao. "
                    f"Approval: {outcome.approval_id or 'nao_disponivel'}.\n"
                    "Para aprovar pelo chat, envie: "
                    f"APROVAR {outcome.approval_id or '<approval_id>'}."
                ),
                intent=intent,
                policy={
                    **policy,
                    "approval_required_for": [intent["requested_operation"]],
                    "approval_actions": ["write_files"],
                    "required_preconditions": ["approval", "validation"],
                    "safe_to_preview": True,
                    "safe_to_execute": False,
                },
                operation_id=decision.operation_id,
                operation_type=public_operation_type,
                message_type="task_status_update",
                requires_user_action=True,
                is_final_answer=False,
                grounded=True,
                evidence_refs=outcome.evidence_refs,
                next_actions=(
                    [ChatNextAction(type="review_approval", label="Revisar aprovacao", target_id=outcome.approval_id)]
                    if outcome.approval_id
                    else []
                ),
                warnings=outcome.warnings,
            )
        if outcome.status == "needs_clarification":
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="needs_clarification",
                message=(
                    "Preciso de um workspace alvo permitido para criar esse arquivo. "
                    "Informe um caminho ou selecione um workspace target_mutable antes de executar a escrita governada."
                ),
                intent=intent,
                policy=policy,
                operation_id=decision.operation_id,
                operation_type=public_operation_type,
                message_type="clarification_request",
                requires_user_action=True,
                is_final_answer=False,
                grounded=True,
                evidence_refs=outcome.evidence_refs,
                warnings=outcome.warnings,
            )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=outcome.run_id,
            status="failed" if outcome.status == "failed" else "blocked",
            message=(
                ("A escrita falhou durante a execucao governada. " if outcome.status == "failed" else "A escrita foi bloqueada pela policy do workspace. ")
                + f"Motivo: {outcome.reason_code or 'workspace_write_denied'}. "
                "Alternativa segura: escolha um workspace target_mutable ou gere um artifact fora do projeto fonte."
            ),
            intent=intent,
            policy=policy,
            operation_id=decision.operation_id,
            operation_type=public_operation_type,
            message_type="blocked_policy_message",
            requires_user_action=False,
            is_final_answer=False,
            grounded=True,
            evidence_refs=outcome.evidence_refs,
            warnings=outcome.warnings,
        )

    def _chat_write_requires_approval(self, request: GovernedWriteRequest, workspace) -> bool:
        if self.require_chat_write_approval is not None:
            return bool(self.require_chat_write_approval)
        policy = load_yaml_file(PATHS.config_root / "agents" / "tool_gateway_policy.yaml", critical=False, root=PATHS.config_root / "agents")
        approval_cfg = policy.get("approval", {}) if isinstance(policy, dict) else {}
        if not bool(approval_cfg.get("require_human_approval_for_chat_workspace_write", True)):
            return False
        action_set = {str(item) for item in approval_cfg.get("side_effect_actions", []) or []}
        requested = {request.operation_type, *request.requested_capabilities}
        return bool(action_set.intersection(requested)) and workspace.workspace_role in {"target_mutable", "system_mutable"}

    def _negative_constraint_flags(self, prompt: str, decision: ChatOperationDecision) -> dict[str, object]:
        lowered = self._normalize(prompt)
        patterns = {
            "write": [
                "nao crie arquivo",
                "nao escreva arquivo",
                "nao gere relatorio",
                "nao implemente",
                "nao altere arquivos",
                "nao modifique arquivos",
                "sem criar arquivo",
                "sem gerar relatorio",
                "sem alterar arquivos",
                "read-only",
                "readonly",
                "somente leitura",
                "apenas leia",
                "leia apenas",
                "apenas metadados",
            ],
            "shell": ["nao execute shell", "sem shell", "nao rode comando", "nao execute comando"],
            "chat_only": ["responda somente no chat", "responda apenas no chat", "somente no chat", "apenas no chat"],
        }
        matched = [term for terms in patterns.values() for term in terms if term in lowered]
        chat_only = any(term in lowered for term in patterns["chat_only"])
        write_blocked = bool(matched) or bool(decision.metadata.get("read_only") is True or decision.metadata.get("workspace_write") is False)
        shell_blocked = any(term in lowered for term in patterns["shell"]) or write_blocked
        return {
            "write_allowed": False if write_blocked else True,
            "shell_allowed": False if shell_blocked else True,
            "report_file_allowed": False if any(term in lowered for term in ["nao gere relatorio", "sem gerar relatorio"]) else True,
            "chat_only": chat_only,
            "readonly": write_blocked,
            "matched_constraints": matched,
        }

    def _normalize(self, value: str) -> str:
        import unicodedata

        decomposed = unicodedata.normalize("NFKD", value)
        ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
        return ascii_text.casefold()
