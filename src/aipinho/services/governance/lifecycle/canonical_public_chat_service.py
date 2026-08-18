from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.governance.lifecycle import GovernanceLifecycleSnapshot
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.chat.chat_artifact_fulfillment_service import ChatArtifactFulfillmentService
from aipinho.services.chat.artifact_request_preview_service import ArtifactRequestPreviewService
from aipinho.services.chat.chat_operation_router_service import ChatOperationRouterService, ChatOperationDecision
from aipinho.services.chat.followup_result_recall_service import FollowupResultRecallService
from aipinho.services.chat.followup_result_review_service import FollowupResultReviewService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.permission_status_response_service import PermissionStatusResponseService
from aipinho.services.chat.session_diagnostic_service import SessionDiagnosticService
from aipinho.services.governance.capabilities.capability_truth_service import CapabilityTruthService
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService
from aipinho.services.governance.lifecycle.public_route_lifecycle_service import PublicRouteLifecycleService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.patching.execution_preview_compiler import ExecutionPreviewCompiler
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService
from aipinho.services.rag.integration.context_prompt_policy_service import ContextPromptPolicyService
from aipinho.services.semantic_runtime.semantic_proposition_normalization_service import SemanticPropositionNormalizationService
from aipinho.services.sandbox.project_templates import android_kotlin_simple_game_template
from aipinho.services.session.session_store import utc_now


class CanonicalPublicChatService:
    """Canonical public chat entrypoint.

    Public routes resolve the governance lifecycle before invoking legacy/domain
    services. Legacy chat remains available for ordinary conversation content,
    but it no longer owns operational intent, permission, preview, or approval
    decisions on public endpoints.
    """

    _WINDOWS_PATH_RE = re.compile(
        r'(?P<path>[A-Za-z]:[\\/].*?)'
        r'(?=(?:\s+(?:workspace|workload|fonte|source|target|alvo|futuro|comece|nao|não|retorne|responda|faca|faça|crie|implemente|utilize|use|objetivo|esperado|expected)\b)|(?:\s+[A-Za-z]:[\\/])|["\n\r<>|]|$)',
        re.IGNORECASE,
    )
    _NAMED_CONTAINER_RE = re.compile(
        r"(?is)\b(?:pasta|diretorio|diret[oó]rio|projeto|workspace)\s+"
        r"(?:chamad[ao]|nomead[ao]|de\s+nome)?\s*[\"'“”`]*"
        r"(?P<name>[A-Za-z0-9_. -]{2,80}?)[\"'“”`]*\s+"
        r"(?:dentro|em|no|na)\s+",
    )

    def __init__(
        self,
        *,
        chat_service: ChatService | None = None,
        lifecycle_public: PublicRouteLifecycleService | None = None,
        lifecycle: GovernanceLifecycleService | None = None,
        approval_commands: ChatApprovalCommandService | None = None,
        permission_status: PermissionStatusResponseService | None = None,
        draft_store: TaskDraftStore | None = None,
        preview_service: TaskPreviewService | None = None,
        approval_service: ApprovalService | None = None,
        capability_truth: CapabilityTruthService | None = None,
        project_analysis: ProjectAnalysisService | None = None,
        readonly_artifact_runtime: ReadonlyAnalysisArtifactRuntimeService | None = None,
        workspace_policy: WorkspacePolicyService | None = None,
        context_prompt_policy: ContextPromptPolicyService | None = None,
        operation_router: ChatOperationRouterService | None = None,
        artifact_fulfillment: ChatArtifactFulfillmentService | None = None,
        artifact_preview: ArtifactRequestPreviewService | None = None,
        followup_recall: FollowupResultRecallService | None = None,
        followup_review: FollowupResultReviewService | None = None,
        session_diagnostic: SessionDiagnosticService | None = None,
    ) -> None:
        self.chat_service = chat_service or ChatService()
        self.lifecycle = lifecycle or GovernanceLifecycleService()
        self.lifecycle_public = lifecycle_public or PublicRouteLifecycleService(lifecycle=self.lifecycle)
        self.approval_commands = approval_commands or ChatApprovalCommandService()
        self.permission_status = permission_status or PermissionStatusResponseService()
        self.draft_store = draft_store or TaskDraftStore()
        self.preview_service = preview_service or TaskPreviewService(draft_store=self.draft_store)
        self.approval_service = approval_service or ApprovalService(
            preview_service=self.preview_service,
            draft_store=self.draft_store,
        )
        self.capability_truth = capability_truth or CapabilityTruthService()
        self.project_analysis = project_analysis or ProjectAnalysisService()
        self.readonly_artifact_runtime = (
            readonly_artifact_runtime or ReadonlyAnalysisArtifactRuntimeService()
        )
        self.execution_preview_compiler = ExecutionPreviewCompiler()
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()
        self.context_prompt_policy = context_prompt_policy or ContextPromptPolicyService()
        self.operation_router = operation_router or ChatOperationRouterService()
        self._artifact_fulfillment = artifact_fulfillment
        self.artifact_preview = artifact_preview or ArtifactRequestPreviewService()
        self.followup_recall = followup_recall or FollowupResultRecallService()
        self.followup_review = followup_review or FollowupResultReviewService()
        self.session_diagnostic = session_diagnostic or SessionDiagnosticService()
        self.semantic_propositions = SemanticPropositionNormalizationService()

    @property
    def artifact_fulfillment(self) -> ChatArtifactFulfillmentService:
        if self._artifact_fulfillment is None:
            self._artifact_fulfillment = ChatArtifactFulfillmentService()
        return self._artifact_fulfillment

    def respond(self, request: ChatRequest, *, source_channel: str) -> ChatResponse:
        workspace = self._workspace_from_request(request)
        initial = self.lifecycle.evaluate(
            user_text=request.message,
            source_channel=source_channel,
            session_id=request.session_id,
            workspace_path=workspace,
        )
        intent_type = initial.intent.intent_type

        if intent_type == "approval_command":
            return self._approval_command_response(request, source_channel=source_channel, snapshot=initial)

        context_policy = self.context_prompt_policy.evaluate_user_message(request.message)
        if not context_policy.allowed:
            return self._context_prompt_policy_block_response(request, initial, context_policy)

        if intent_type == "workspace_permission_list":
            response = self.permission_status.respond(
                session_id=request.session_id,
                operation_id=initial.operation_contract.operation_id,
                operation_type="workspace_permission_list",
            )
            return self.lifecycle_public.finalize_chat_response(
                response,
                prompt=request.message,
                source_channel=source_channel,
                workspace_path=workspace,
            )

        if intent_type == "capability_truth":
            return self._capability_truth_response(request, initial)

        if intent_type in {"meta_conversation", "conversation_self_diagnosis"}:
            return self._meta_conversation_response(request, initial)

        if initial.intent.readonly and intent_type in {"product_planning_readonly", "session_diagnostic", "workspace_analysis_readonly"}:
            return self._readonly_response(request, initial)

        if intent_type == "workspace_fix_request":
            return self._fix_request_discovery_response(request, initial, workspace=workspace)

        if initial.intent.side_effect_requested or initial.operation_contract.requested_actions:
            return self._governed_operation_response(request, source_channel=source_channel, workspace=workspace, initial=initial)

        client_operation = self._client_operation_response(
            request,
            source_channel=source_channel,
            workspace=workspace,
        )
        if client_operation is not None:
            return self.lifecycle_public.finalize_chat_response(
                client_operation,
                prompt=request.message,
                source_channel=source_channel,
                workspace_path=workspace,
            )

        return self._conversation_response(request, source_channel=source_channel, workspace=workspace)

    def _client_operation_response(
        self,
        request: ChatRequest,
        *,
        source_channel: str,
        workspace: str | None,
    ) -> ChatResponse | None:
        decision = self.operation_router.route(request.message, workspace_hint=workspace)
        routed_type = self._routed_operation_type(decision)
        session_id = request.session_id or "chat_default"
        if routed_type in {"workspace_permission_list", "permission_status"}:
            return self.permission_status.respond(
                session_id=session_id,
                operation_id=decision.operation_id,
                operation_type=routed_type,
            )
        if routed_type == "session_diagnostic":
            return self.session_diagnostic.diagnose(session_id, decision)
        if routed_type == "filesystem_archive_request":
            return self.artifact_fulfillment.fulfill_filesystem_archive(
                session_id=session_id,
                decision=decision,
            )
        if routed_type == "artifact_request":
            return self._artifact_request_response(request, decision, source_channel=source_channel, workspace=workspace)
        if routed_type == "followup_result_recall":
            return self.followup_recall.recall(session_id, decision)
        if routed_type == "followup_result_review":
            return self.followup_review.review(session_id, decision)
        if (
            routed_type == "readonly_project_analysis"
            and decision.metadata.get("router_operation_type") == "readonly_project_analysis"
        ):
            return self._readonly_project_analysis_preview_response(
                request,
                decision,
                workspace_ref=workspace or decision.workspace,
            )
        return None

    @staticmethod
    def _routed_operation_type(decision: ChatOperationDecision) -> str:
        return str(decision.metadata.get("router_operation_type") or decision.operation_type)

    def _artifact_request_response(
        self,
        request: ChatRequest,
        decision: ChatOperationDecision,
        *,
        source_channel: str,
        workspace: str | None,
    ) -> ChatResponse:
        factual_response: ChatResponse | None = None
        primary = (decision.primary_prompt or "").strip()
        if primary and primary != request.message.strip():
            factual_response = self._conversation_response(
                request.model_copy(update={"message": primary}),
                source_channel=source_channel,
                workspace=workspace,
            )
        if factual_response is not None and factual_response.status == "ok" and factual_response.message.strip():
            return self.artifact_fulfillment.fulfill_response_artifact(
                session_id=request.session_id or "chat_default",
                decision=decision,
                factual_response=factual_response,
            )
        return self.artifact_preview.offer(decision, factual_response)

    def _readonly_project_analysis_preview_response(
        self,
        request: ChatRequest,
        decision: ChatOperationDecision,
        *,
        workspace_ref: str | None,
    ) -> ChatResponse:
        public_operation_type = str(decision.metadata.get("router_operation_type") or decision.operation_type)
        if not workspace_ref:
            return self._base_response(
                request,
                status="needs_clarification",
                operation_type=public_operation_type,
                message_type="clarification_request",
                message=(
                    "Preciso saber qual workspace ou projeto devo analisar em modo somente leitura. "
                    "Escolha um workspace legivel ou informe um caminho registrado."
                ),
                intent={"intent_type": "readonly_project_analysis", "requires_task": True, "requires_workspace": True},
                policy={"approval_required_for": [], "read_only": True},
                warnings=["workspace_required_but_missing"],
            ).model_copy(update={"requires_user_action": True, "is_final_answer": False, "grounded": False, "grounding_required": True, "grounding_missing_reason": "workspace_missing"})
        return self._base_response(
            request,
            status="preview",
            operation_type=public_operation_type,
            message_type="task_preview",
            message=(
                f"Posso iniciar uma analise somente leitura de {workspace_ref}. "
                "Ainda nao li arquivos nem gerei conclusao sobre o projeto; isto e uma previa operacional. "
                "Nenhuma escrita sera feita nesse workspace por esta resposta."
            ),
            intent={"intent_type": "readonly_project_analysis", "requires_task": True, "requires_workspace": True},
            policy={"approval_required_for": [], "read_only": True, "workspace_id": workspace_ref},
            warnings=["readonly_preview_not_project_summary"],
        ).model_copy(update={"requires_user_action": True, "is_final_answer": False, "grounded": False, "grounding_required": True, "grounding_missing_reason": "read_files_not_executed"})

    def _approval_command_response(
        self,
        request: ChatRequest,
        *,
        source_channel: str,
        snapshot: GovernanceLifecycleSnapshot,
    ) -> ChatResponse:
        response = self.approval_commands.handle(
            request.session_id or "chat_default",
            request.message,
            source_channel=source_channel,
        )
        if response is None:
            response = self._base_response(
                request,
                status="needs_clarification",
                operation_type="approval_command",
                message_type="clarification_request",
                message="Nenhum comando de approval reconhecido. Use APROVAR approval_xxx, NEGAR approval_xxx ou LISTAR APPROVALS PENDENTES.",
                intent={"intent_type": "approval_command", "requires_task": False},
            )
        return self.lifecycle_public.finalize_chat_response(
            response,
            prompt=request.message,
            source_channel=source_channel,
            workspace_path=self._workspace_from_request(request),
        )

    def _readonly_response(self, request: ChatRequest, snapshot: GovernanceLifecycleSnapshot) -> ChatResponse:
        labels = {
            "product_planning_readonly": "PLANNING_READONLY_READY",
            "workspace_analysis_readonly": "WORKSPACE_ANALYSIS_READONLY_READY",
            "session_diagnostic": "SESSION_DIAGNOSTIC_READY",
        }
        label = labels.get(snapshot.intent.intent_type, "READONLY_READY")
        workspace = self._readonly_analysis_workspace(request.message, self._workspace_from_request(request))
        if snapshot.intent.intent_type == "workspace_analysis_readonly" and not workspace:
            workspace = self.readonly_artifact_runtime.workspace_from_phase_dependencies(
                text=request.message,
                session_id=request.session_id,
            )
        if snapshot.intent.intent_type == "workspace_analysis_readonly" and workspace:
            if self.readonly_artifact_runtime.should_handle(
                request.message,
                intent_type=snapshot.intent.intent_type,
                workspace=workspace,
            ):
                execution = self.readonly_artifact_runtime.start_public_boundary(
                    request=request,
                    workspace=workspace,
                    label="WORKSPACE_ANALYSIS_ARTIFACTS_READY",
                )
                return self.lifecycle_public.finalize_chat_response(
                    execution.response,
                    prompt=request.message,
                    source_channel=snapshot.intent.source_channel,
                    workspace_path=workspace,
                )
            return self._workspace_analysis_readonly_response(request, snapshot, workspace, label)
        if snapshot.intent.intent_type == "product_planning_readonly" and workspace and self._looks_like_readonly_project_plan(request.message):
            return self._project_planning_readonly_response(request, snapshot, workspace, label)
        response = self._base_response(
            request,
            status="ok",
            operation_type=snapshot.intent.operation_type,
            message_type="assistant_final_answer",
            message=(
                f"{label}\n"
                "Classifiquei este pedido como leitura/planejamento sem side effects. "
                "Nao criei TaskPreview, ApprovalRequest, grant, shell ou escrita de arquivos."
            ),
            intent={
                "intent_type": snapshot.intent.intent_type,
                "operation_type": snapshot.intent.operation_type,
                "requires_task": False,
                "readonly": True,
                "negative_constraints": snapshot.intent.negative_constraints,
            },
            policy={"read_only": True, "approval_required_for": [], "write_allowed": False, "shell_allowed": False},
        )
        return self._attach_lifecycle(response, snapshot)

    def _context_prompt_policy_block_response(self, request: ChatRequest, snapshot: GovernanceLifecycleSnapshot, decision) -> ChatResponse:
        response = self._base_response(
            request,
            status="blocked",
            operation_type="context_prompt_policy",
            message_type="blocked_policy_message",
            message=decision.message,
            intent={
                "intent_type": snapshot.intent.intent_type,
                "operation_type": "context_prompt_policy",
                "requires_task": False,
                "readonly": True,
            },
            policy={
                "permission": "denied",
                "reason_code": decision.reason_code,
                "context_prompt_policy": {
                    "allowed": decision.allowed,
                    "evidence": decision.evidence,
                },
            },
            warnings=decision.warnings,
        )
        return self._attach_lifecycle(response, snapshot)

    def _project_planning_readonly_response(
        self,
        request: ChatRequest,
        snapshot: GovernanceLifecycleSnapshot,
        workspace: str,
        label: str,
    ) -> ChatResponse:
        target_workspace = self._target_workspace_from_request(request.message, source_workspace=workspace)
        try:
            result = self.project_analysis.analyze_project(
                ProjectAnalysisRequest(
                    workspace=workspace,
                    prompt=request.message,
                    goal="chat_readonly_project_planning",
                    include_trace=False,
                )
            )
            message = self._format_project_planning_message(label, result, target_workspace)
            policy = {
                "read_only": True,
                "approval_required_for": [],
                "write_allowed": False,
                "shell_allowed": False,
                "workspace": workspace,
                "target_workspace": target_workspace,
                "analysis_result_id": result.result_id,
                "analysis_status": result.status,
            }
            contract_preview = {
                "plan_mode": "readonly_textual_plan",
                "workspace": workspace,
                "target_workspace": target_workspace,
                "task_preview_created": False,
                "approval_created": False,
                "tree_status": result.tree_summary.status,
                "candidate_files": result.tree_summary.candidate_files[:20],
                "structures": result.structures,
                "validation_plan": [
                    "review_textual_plan_before_preview",
                    "create_executable_plan_before_approval",
                    "validate_outputs_after_approved_execution",
                ],
            }
            status = "ok" if result.status in {"ok", "partial"} else "degraded"
        except Exception as exc:
            message = (
                f"{label}\n"
                "Planejamento read-only reconhecido, mas a analise do workspace falhou antes de qualquer side effect.\n"
                f"reason_code=readonly_planning_analysis_failed; detail={type(exc).__name__}\n"
                "Nenhuma escrita, shell, patch, artifact, TaskRun ou ApprovalRequest foi criado."
            )
            policy = {
                "read_only": True,
                "approval_required_for": [],
                "write_allowed": False,
                "shell_allowed": False,
                "workspace": workspace,
                "target_workspace": target_workspace,
                "reason_code": "readonly_planning_analysis_failed",
            }
            contract_preview = {
                "plan_mode": "readonly_textual_plan",
                "workspace": workspace,
                "target_workspace": target_workspace,
                "reason_code": "readonly_planning_analysis_failed",
            }
            status = "degraded"

        response = self._base_response(
            request,
            status=status,
            operation_type=snapshot.intent.operation_type,
            message_type="assistant_final_answer",
            message=message,
            intent={
                "intent_type": snapshot.intent.intent_type,
                "operation_type": snapshot.intent.operation_type,
                "requires_task": False,
                "readonly": True,
                "negative_constraints": snapshot.intent.negative_constraints,
            },
            policy=policy,
            contract_preview=contract_preview,
        )
        return self._attach_lifecycle(response, snapshot)

    def _workspace_analysis_readonly_response(
        self,
        request: ChatRequest,
        snapshot: GovernanceLifecycleSnapshot,
        workspace: str,
        label: str,
    ) -> ChatResponse:
        try:
            result = self.project_analysis.analyze_project(
                ProjectAnalysisRequest(
                    workspace=workspace,
                    prompt=request.message,
                    goal="chat_readonly_workspace_analysis",
                    include_trace=False,
                )
            )
            message = self._format_workspace_analysis_message(label, result)
            policy = {
                "read_only": True,
                "approval_required_for": [],
                "write_allowed": False,
                "shell_allowed": False,
                "workspace": workspace,
                "analysis_result_id": result.result_id,
                "analysis_status": result.status,
            }
            contract_preview = {
                "workspace": workspace,
                "tree_status": result.tree_summary.status,
                "total_files_seen": result.tree_summary.total_files_seen,
                "total_dirs_seen": result.tree_summary.total_dirs_seen,
                "structures": result.structures,
                "findings": [finding.model_dump() for finding in result.findings[:8]],
                "warnings": result.warnings,
                "violations": result.violations,
            }
            if result.status in {"ok", "partial"}:
                status = "ok"
            elif result.status == "blocked":
                status = "blocked"
            else:
                status = "degraded"
        except Exception as exc:
            message = (
                f"{label}\n"
                "Classifiquei como analise read-only, mas a inspecao controlada falhou antes de qualquer side effect.\n"
                f"reason_code=readonly_analysis_failed; detail={type(exc).__name__}\n"
                "Nenhuma escrita, shell, patch, artifact, TaskRun ou ApprovalRequest foi criado."
            )
            policy = {
                "read_only": True,
                "approval_required_for": [],
                "write_allowed": False,
                "shell_allowed": False,
                "workspace": workspace,
                "reason_code": "readonly_analysis_failed",
            }
            contract_preview = {"workspace": workspace, "reason_code": "readonly_analysis_failed"}
            status = "degraded"

        response = self._base_response(
            request,
            status=status,
            operation_type=snapshot.intent.operation_type,
            message_type="assistant_final_answer",
            message=message,
            intent={
                "intent_type": snapshot.intent.intent_type,
                "operation_type": snapshot.intent.operation_type,
                "requires_task": False,
                "readonly": True,
                "negative_constraints": snapshot.intent.negative_constraints,
            },
            policy=policy,
            contract_preview=contract_preview,
        )
        return self._attach_lifecycle(response, snapshot)

    def _format_workspace_analysis_message(self, label: str, result) -> str:
        tree = result.tree_summary
        report = result.report
        top_level = ", ".join(tree.top_level[:20]) or "nenhum item top-level detectado"
        important = ", ".join(tree.important_paths[:20]) or "nenhum caminho importante detectado"
        candidates = ", ".join(tree.candidate_files[:20]) or "nenhum arquivo candidato detectado"
        structures = ", ".join(result.structures[:20]) or "nao detectadas"
        findings = "\n".join(
            f"- {item.severity.upper()}: {item.title} | {item.summary}"
            for item in result.findings[:8]
        ) or "- Nenhum finding automatizado forte com as evidencias lidas."
        warnings = "\n".join(f"- {item}" for item in result.warnings[:8]) or "- Nenhum warning relevante."
        violations = "\n".join(f"- {item}" for item in result.violations[:8]) or "- Nenhuma violacao de leitura reportada."
        sections = "\n".join(
            f"- {section.get('title', 'Secao')}: {section.get('content') or ', '.join(map(str, section.get('items', [])[:8]))}"
            for section in report.sections[:6]
        ) or "- Relatorio sem secoes adicionais."
        return (
            f"{label}\n"
            "Speaker Truth: modo read-only confirmado. Nao criei TaskPreview, ApprovalRequest, grant, shell, patch, artifact ou escrita de arquivos.\n\n"
            "Fase atual: Fase A / discovery e diagnostico read-only.\n\n"
            "Campos da Fase 0:\n"
            "- intent_type: workspace_analysis_readonly\n"
            "- operation_type: workspace_analysis_readonly\n"
            "- readonly: true\n"
            "- side_effect_requested: false\n"
            "- requested_actions: []\n"
            "- policy.permission: allowed/read_only\n"
            "- approval_required: false\n"
            "- approval_id: null\n"
            "- task_id: null\n"
            "- runtime_profile: workspace_analysis_readonly\n\n"
            "Provas:\n"
            f"- workspace: {tree.workspace}\n"
            f"- tree_status: {tree.status}\n"
            f"- arquivos vistos: {tree.total_files_seen}; diretorios vistos: {tree.total_dirs_seen}\n"
            f"- top_level: {top_level}\n"
            f"- caminhos importantes: {important}\n"
            f"- arquivos candidatos: {candidates}\n\n"
            "Stack provavel / architecture map:\n"
            f"- estruturas detectadas: {structures}\n"
            f"- resumo: {report.summary}\n\n"
            "Diagnostico tecnico read-only:\n"
            f"{findings}\n\n"
            "Secoes do relatorio interno:\n"
            f"{sections}\n\n"
            "Suspeitas e limitacoes:\n"
            f"{warnings}\n"
            f"{violations}\n\n"
            "Technical project plan / sprint roadmap:\n"
            "- Sprint 1: confirmar stack e entrypoints usando somente arquivos ja detectados.\n"
            "- Sprint 2: escolher um patch minimo com arquivos-alvo reais e rollback plan.\n"
            "- Sprint 3: criar TaskPreview somente se houver plano executavel, expected outputs e validation plan.\n"
            "- Sprint 4: aguardar aprovacao explicita antes de qualquer escrita ou shell.\n"
            "- Sprint 5: executar patch aprovado e validar sem ampliar escopo.\n\n"
            "TaskPreview: nao criada nesta fase read-only.\n"
            "ApprovalRequest: nao criado por restricao explicita do prompt.\n"
            "Validation proposta: quando houver patch futuro, validar diff aprovado, outputs esperados e ausencia de side effects fora do escopo.\n"
            "Veredito final: READONLY_DISCOVERY_OK_READY_FOR_PATCH_PREVIEW"
        )

    def _format_project_planning_message(self, label: str, result, target_workspace: str | None) -> str:
        tree = result.tree_summary
        report = result.report
        target = target_workspace or "alvo ainda nao resolvido"
        important = tree.important_paths[:16] or tree.candidate_files[:16] or tree.top_level[:16]
        important_lines = "\n".join(f"- {item}" for item in important) or "- Nenhum arquivo candidato forte detectado."
        findings = "\n".join(
            f"- {item.severity.upper()}: {item.title} | {item.summary}"
            for item in result.findings[:8]
        ) or "- Nenhum finding automatizado forte com as evidencias lidas."
        structures = ", ".join(result.structures[:20]) or "nao detectadas"
        return (
            f"{label}\n"
            "Plano governado read-only gerado. Nao criei TaskPreview real, ApprovalRequest, grant, shell, patch, artifact ou escrita de arquivos.\n\n"
            "Objetivo do plano:\n"
            f"- Fonte analisada em modo read-only: {tree.workspace}\n"
            f"- Alvo futuro: {target}\n"
            "- Preparar uma futura reconstrucao governada, mas somente depois de existir plano executavel completo e approval aplicavel.\n\n"
            "Resumo tecnico da fonte:\n"
            f"- tree_status: {tree.status}\n"
            f"- arquivos vistos: {tree.total_files_seen}; diretorios vistos: {tree.total_dirs_seen}\n"
            f"- estruturas detectadas: {structures}\n"
            f"- resumo: {report.summary}\n\n"
            "Arquivos e areas provaveis para uma futura TaskPreview:\n"
            f"{important_lines}\n\n"
            "Plano de acao em fases:\n"
            "1. Discovery confirmado: manter a fonte somente para leitura e congelar evidencias usadas no plano.\n"
            "2. Blueprint: definir stack, entrypoints, telas/componentes, assets e configuracoes minimas do projeto alvo.\n"
            "3. Plano executavel: listar arquivos reais a criar/modificar no alvo, expected outputs, validation plan e rollback plan.\n"
            "4. Approval futuro: criar ApprovalRequest somente quando o plano executavel tiver target_paths reais e preview_hash.\n"
            "5. Execucao governada: aplicar apenas o plano aprovado, sem escrever na fonte read-only.\n"
            "6. Validacao: checar arquivos criados, build/test quando permitido, ausencia de escrita na fonte e status final sem falso sucesso.\n\n"
            "Riscos e atencoes:\n"
            f"{findings}\n\n"
            "Rollback futuro:\n"
            "- Registrar pre-state do alvo antes de escrever.\n"
            "- Criar/modificar arquivos por lote pequeno e rastreavel.\n"
            "- Reverter somente os arquivos do alvo tocados pelo plano aprovado.\n"
            "- Nunca usar rollback para alterar a fonte read-only.\n\n"
            "Validation proposta para fase futura:\n"
            "- target_paths_match_preview\n"
            "- expected_outputs_present\n"
            "- no_write_to_source_workspace\n"
            "- generated_files_exist\n"
            "- build_or_smoke_result_when_shell_is_approved\n"
            "- speaker_truth_no_success_before_validation\n\n"
            "Status: READONLY_PROJECT_PLAN_READY"
        )

    def _fix_request_discovery_response(
        self,
        request: ChatRequest,
        snapshot: GovernanceLifecycleSnapshot,
        *,
        workspace: str | None,
    ) -> ChatResponse:
        status_label = "WORKSPACE_DISCOVERY_REQUIRED" if workspace else "APPROVAL_NOT_CREATED_WORKSPACE_NOT_RESOLVED"
        response = self._base_response(
            request,
            status="preview",
            operation_type="workspace_fix_request",
            message_type="task_preview",
            message=(
                f"{status_label}\n"
                "Pedido de correcao identificado como fluxo em duas fases. Primeiro preciso fazer discovery/diagnostico read-only, "
                "identificar arquivos-alvo e gerar plano executavel. Nenhum ApprovalRequest de escrita foi criado."
            ),
            intent={
                "intent_type": "workspace_fix_request",
                "operation_type": "workspace_fix_request",
                "requires_task": True,
                "readonly_first_phase": True,
            },
            policy={
                "write_approval_created": False,
                "reason_code": status_label,
                "required_before_write_approval": ["workspace_snapshot_ref", "analysis_ref", "target_files", "executable_plan_ref"],
            },
            actions=[],
            contract_preview={
                "phase": "discovery_first",
                "workspace": workspace,
                "next_status": "PROJECT_DIAGNOSIS_READY",
            },
        )
        return self._attach_lifecycle(response, snapshot)

    def _capability_truth_response(self, request: ChatRequest, snapshot: GovernanceLifecycleSnapshot) -> ChatResponse:
        message, payload = self.capability_truth.answer()
        response = self._base_response(
            request,
            status="ok",
            operation_type="capability_truth",
            message_type="assistant_final_answer",
            message=message,
            intent={"intent_type": "capability_truth", "requires_task": False, "readonly": True},
            policy={"capability_truth_source": "CapabilityTruthService", **payload},
        )
        return self._attach_lifecycle(response, snapshot)

    def _meta_conversation_response(self, request: ChatRequest, snapshot: GovernanceLifecycleSnapshot) -> ChatResponse:
        semantic_intent = snapshot.intent.intent_type
        message = (
            "Nao ha evidencia de confusao de intent nesta mensagem: o lifecycle canonico a classificou como "
            f"`{semantic_intent}` e o contrato operacional permaneceu `conversation`, sem Task, Approval, patch, shell ou workspace analysis. "
            "Quando uma resposta conversacional falha ou fica degradada, a causa deve ser atribuida ao runtime/modelo speaker, "
            "ao fallback ou a uma ausencia de saida textual, nao a uma promocao operacional que nao aconteceu."
        )
        response = self._base_response(
            request,
            status="ok",
            operation_type="conversation",
            message_type="assistant_final_answer",
            message=message,
            intent={
                "intent_type": semantic_intent,
                "operation_type": "conversation",
                "requires_task": False,
                "meta_conversation": True,
                "diagnostic_scope": "conversation_runtime_truth",
            },
            policy={
                "allowed_actions": [],
                "safe_to_execute": False,
                "conversation_response_allowed": True,
                "policy_scope": "operational_actions_only",
                "truth_claim_type": "diagnostic_explanation",
            },
            warnings=["meta_conversation_routed_without_workspace_analysis"],
        )
        return self._attach_lifecycle(response, snapshot)

    def _conversation_response(self, request: ChatRequest, *, source_channel: str, workspace: str | None) -> ChatResponse:
        try:
            response = self.chat_service.respond(request)
        except Exception as exc:
            response = self._base_response(
                request,
                status="degraded",
                operation_type="conversation",
                message_type="assistant_degraded_answer",
                message=f"O chat legado falhou de forma controlada. reason_code=legacy_chat_failed; detalhe={type(exc).__name__}",
                intent={"intent_type": "conversation", "requires_task": False},
                policy={"legacy_chat_failed": True},
            )
        return self.lifecycle_public.finalize_chat_response(
            response,
            prompt=request.message,
            source_channel=source_channel,
            workspace_path=workspace,
        )

    def _governed_operation_response(
        self,
        request: ChatRequest,
        *,
        source_channel: str,
        workspace: str | None,
        initial: GovernanceLifecycleSnapshot,
    ) -> ChatResponse:
        metadata = self._operation_metadata(
            request.message,
            initial.intent.operation_type,
            workspace,
            session_id=request.session_id,
        )
        workspace_block = self._workspace_policy_block(request, metadata)
        if workspace_block is not None:
            return workspace_block
        snapshot = self.lifecycle.evaluate(
            user_text=request.message,
            source_channel=source_channel,
            session_id=request.session_id,
            requested_actions=metadata["requested_actions"],
            operation_type=metadata["operation_type"],
            contract_type=metadata["contract_type"],
            runtime_profile=metadata["runtime_profile"],
            target_paths=metadata["target_paths"],
            workspace_path=metadata["workspace_path"],
            executable_plan_ref=metadata["executable_plan_ref"],
            plan_kind=metadata["plan_kind"],
            expected_outputs=metadata["expected_outputs"],
            source_message_id=metadata["source_message_id"],
            context_ref=metadata["context_ref"],
            discovery_ref=metadata["discovery_ref"],
            analysis_ref=metadata["analysis_ref"],
            validation_plan=metadata["validation_plan"],
            rollback_plan=metadata["rollback_plan"],
            plan_payload=metadata["plan_payload"],
        )
        if not snapshot.approval_gate.can_create_approval:
            return self._plan_only_or_blocked_response(request, snapshot, metadata)
        try:
            draft, preview, approval = self._persist_executable_preview(request, snapshot, metadata)
        except ValueError as exc:
            response = self._base_response(
                request,
                status="preview",
                operation_type=metadata["operation_type"],
                message_type="task_preview",
                message=(
                    "APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN\n"
                    f"reason_code={str(exc)}\n"
                    "Criei apenas um preview conceitual; nenhuma execucao foi iniciada."
                ),
                intent={"intent_type": snapshot.intent.intent_type, "requires_task": True},
                policy={"approval_required_for": metadata["requested_actions"], "approval_created": False, "reason_code": str(exc)},
                actions=metadata["requested_actions"],
                contract_preview=metadata["contract_preview"],
            )
            return self._attach_lifecycle(response, snapshot)

        snapshot.approval_gate.approval_id = approval.approval_id
        snapshot.approval_gate.preview_id = preview.preview_id
        snapshot.approval_gate.draft_id = draft.draft_id
        snapshot.trace.append(
            {
                "stage": "approval_persisted",
                "approval_id": approval.approval_id,
                "preview_id": preview.preview_id,
                "draft_id": draft.draft_id,
            }
        )
        response = self._base_response(
            request,
            status="pending_approval",
            operation_type=snapshot.operation_contract.operation_type,
            message_type="task_preview",
            message=(
                "CANONICAL_PENDING_APPROVAL\n"
                f"approval_id: {approval.approval_id}\n"
                f"preview_id: {preview.preview_id}\n"
                f"task_draft_id: {draft.draft_id}\n"
                f"operation_id: {snapshot.operation_contract.operation_id}\n"
                f"acoes: {', '.join(metadata['requested_actions'])}\n"
                "Nenhuma escrita, shell ou patch foi executado. Para aprovar: "
                f"APROVAR {approval.approval_id}"
            ),
            intent={"intent_type": snapshot.intent.intent_type, "requires_task": True},
            policy={
                "permission": "ask",
                "approval_required_for": metadata["requested_actions"],
                "approval_created": True,
                "canonical_lifecycle_source": "GovernanceLifecycleService",
            },
            actions=metadata["requested_actions"],
            contract_preview=metadata["contract_preview"],
            warnings=[],
            task_draft_id=draft.draft_id,
            preview_id=preview.preview_id,
            approval_id=approval.approval_id,
            next_actions=[
                ChatNextAction(type="approval", label="Aprovar", target_id=approval.approval_id),
                ChatNextAction(type="approval", label="Negar", target_id=approval.approval_id),
            ],
            requires_user_action=True,
        )
        return self._attach_lifecycle(response, snapshot)

    def _workspace_policy_block(self, request: ChatRequest, metadata: dict[str, Any]) -> ChatResponse | None:
        candidates = [
            *list(metadata.get("target_paths") or []),
            metadata.get("primary_target_path"),
            metadata.get("workspace_path"),
        ]
        checked: set[str] = set()
        for candidate in candidates:
            if not candidate:
                continue
            path = str(candidate)
            if path in checked:
                continue
            checked.add(path)
            decision = self.workspace_policy.evaluate(workspace_path=path, requires_workspace=True)
            if decision.blocked:
                reason = decision.reason or "workspace_policy_denied"
                message = (
                    "POLICY_DENIED\n"
                    f"reason_code: {reason}\n"
                    f"operation_type: {metadata['operation_type']}\n"
                    f"target_path: {path}\n"
                    "Nenhum preview, ApprovalRequest, TaskRun, shell ou escrita foi criado."
                )
                return self._base_response(
                    request,
                    status="blocked",
                    operation_type=metadata["operation_type"],
                    message_type="blocked_policy_message",
                    message=message,
                    intent={"intent_type": metadata["operation_type"], "requires_task": True},
                    policy={
                        "permission": "denied",
                        "approval_required_for": [],
                        "approval_created": False,
                        "reason_code": reason,
                        "workspace_policy_status": decision.status,
                    },
                    actions=metadata["requested_actions"],
                    contract_preview={
                        **metadata["contract_preview"],
                        "blocked_target_path": path,
                        "workspace_policy_trace": [item.model_dump() for item in decision.trace],
                    },
                    warnings=[reason],
                    requires_user_action=False,
                )
        return None

    def _plan_only_or_blocked_response(
        self,
        request: ChatRequest,
        snapshot: GovernanceLifecycleSnapshot,
        metadata: dict[str, Any],
    ) -> ChatResponse:
        status = "blocked" if snapshot.state.value == "blocked" and snapshot.policy.permission.value == "denied" else "preview"
        reason = snapshot.approval_gate.reason_code.value if snapshot.approval_gate.reason_code.value != "none" else snapshot.reason_code.value
        label = snapshot.approval_gate.status if snapshot.approval_gate.status != "not_required" else reason
        message = (
            f"{label}\n"
            f"reason_code: {reason}\n"
            f"operation_type: {metadata['operation_type']}\n"
            f"actions_requested: {', '.join(metadata['requested_actions']) or 'nenhuma'}\n"
            "Nenhuma execucao foi iniciada. Gere discovery/contexto, target_paths reais, plano executavel, expected outputs e validation plan antes de approval."
        )
        response = self._base_response(
            request,
            status=status,
            operation_type=metadata["operation_type"],
            message_type="task_preview" if status == "preview" else "blocked_policy_message",
            message=message,
            intent={"intent_type": snapshot.intent.intent_type, "requires_task": snapshot.intent.requires_task},
            policy={
                "permission": snapshot.policy.permission.value,
                "approval_required_for": metadata["requested_actions"] if snapshot.policy.requires_approval else [],
                "approval_created": False,
                "reason_code": snapshot.reason_code.value,
            },
            actions=metadata["requested_actions"],
            contract_preview=metadata["contract_preview"],
            requires_user_action=False,
        )
        return self._attach_lifecycle(response, snapshot)

    def _persist_executable_preview(
        self,
        request: ChatRequest,
        snapshot: GovernanceLifecycleSnapshot,
        metadata: dict[str, Any],
    ):
        now = utc_now()
        draft_id = f"draft_{uuid4().hex}"
        intent_map = {
            "prompt": request.message,
            "raw_prompt": request.message,
            "intent": snapshot.intent.intent_type,
            "risk": snapshot.operation_contract.risk_level,
            "target_path": metadata["primary_target_path"],
            "target_paths": metadata["target_paths"],
            "requested_operation": metadata["operation_type"],
            "concrete_file_operations": metadata["concrete_file_operations"],
            "project_generation_plan": metadata["project_generation_plan"],
            "patch_plan": metadata["patch_plan"],
            "execution_intent": metadata["execution_intent"],
            "executable_patch_plan": metadata["executable_patch_plan"],
            "execution_preview": metadata["execution_preview"],
            "shell_plan": metadata["shell_plan"],
            "source_message_id": metadata["source_message_id"],
            "context_ref": metadata["context_ref"],
            "discovery_ref": metadata["discovery_ref"],
            "analysis_ref": metadata["analysis_ref"],
            "validation_plan": metadata["validation_plan"],
            "rollback_plan": metadata["rollback_plan"],
        }
        draft = TaskContractDraft(
            draft_id=draft_id,
            session_id=request.session_id,
            status="approval_required",
            intent_map=intent_map,
            policy_decision={
                "decision_id": snapshot.lifecycle_id,
                "status": "needs_approval",
                "allowed_actions": [],
                "denied_actions": [],
                "approval_required_for": metadata["requested_actions"],
                "granted_capabilities": [],
                "denied_capabilities": [],
            },
            contract_type=snapshot.operation_contract.contract_type,
            operation_type=snapshot.operation_contract.operation_type,
            intent_type=snapshot.intent.intent_type,
            runtime_profile=snapshot.operation_contract.runtime_profile,
            capabilities_required=metadata["capabilities_required"],
            source_scope="canonical_public_chat",
            requires_workspace=True,
            workspace=TaskDraftWorkspace(path=metadata["workspace_path"], status="confirmed"),
            requested_actions=metadata["requested_actions"],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=metadata["requested_actions"],
            executable_plan_ref=metadata["executable_plan_ref"],
            expected_outcomes=metadata["expected_outputs"],
            safe_to_execute=False,
            safe_to_preview=True,
            warnings=[],
            trace=[
                {"stage": "canonical_public_chat", "lifecycle_id": snapshot.lifecycle_id},
                {"stage": "canonical_contract", "operation_id": snapshot.operation_contract.operation_id},
                {"stage": "context_gate", "status": snapshot.context_gate.status},
                {"stage": "preview_quality_gate", "status": snapshot.preview_quality.status},
            ],
            created_at=now,
            updated_at=now,
        )
        self.draft_store.save(draft)
        preview = self.preview_service.create_preview_from_draft(draft_id)
        if preview is None:
            raise ValueError("preview_not_created")
        approval = self.approval_service.create_approval_for_preview(
            preview.preview_id,
            actions=metadata["requested_actions"],
            actor=Actor(type="user", id="chat_user"),
            reason="canonical_public_chat_pending_approval",
        )
        return draft, preview, approval

    def _operation_metadata(
        self,
        text: str,
        operation_type: str,
        workspace: str | None,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        paths = self._extract_paths(text)
        if workspace:
            paths.insert(0, workspace)
        paths = list(dict.fromkeys(paths))
        execution_intent: dict[str, Any] = {}
        executable_patch_plan: dict[str, Any] = {}
        execution_preview: dict[str, Any] = {}
        folder_name = None if operation_type == "run_command" else self._extract_named_container(text)
        labeled_target = self._target_workspace_from_request(text, source_workspace=None)
        base_path = labeled_target or workspace or (paths[-1] if paths else None)
        primary_target = self._target_path(base_path, folder_name)
        target_paths = [primary_target] if primary_target else paths

        normalized = text.casefold()
        semantic_graph = self.semantic_propositions.normalize(text)
        if any(token in normalized for token in ("pasta", "diretorio", "diretório")) and primary_target:
            op_type = "filesystem_create_directory"
            actions = ["create_directory"]
            contract_type = "filesystem_write"
            runtime_profile = "write_file"
            plan_kind = "concrete_file_operations"
            concrete = [{"action": "create_directory", "target_path": primary_target}]
            project_plan: dict[str, Any] = {}
            patch_plan: dict[str, Any] = {}
            expected = ["filesystem_operation", "validation_result"]
        elif operation_type in {"project_bootstrap", "project_generation"}:
            op_type = "project_generation"
            actions = ["write_files"]
            contract_type = "project_generation"
            runtime_profile = "project_generation"
            plan_kind = "project_generation_plan"
            project_plan = self._project_generation_plan(primary_target or base_path, text)
            concrete = []
            patch_plan = {}
            expected = ["project_generation", "validation_result"]
        elif operation_type in {"run_command"}:
            op_type = "run_command"
            actions = ["run_command"]
            contract_type = "shell_execution"
            runtime_profile = "shell"
            plan_kind = "shell_plan"
            concrete = []
            project_plan = {}
            patch_plan = {}
            shell_plan = self._shell_plan(primary_target or base_path, text)
            expected = ["command_result", "validation_result"]
        else:
            op_type = (
                "patch_request"
                if operation_type in {"patch_request", "patch_apply"} or semantic_graph.state_effect in {"workspace_mutation", "proposal_only"}
                else "filesystem_write_file"
            )
            actions = ["apply_patch"] if op_type == "patch_request" else ["write_files"]
            contract_type = "patch_request" if op_type == "patch_request" else "filesystem_write"
            runtime_profile = "patch" if op_type == "patch_request" else "write_file"
            plan_kind = "patch_plan" if op_type == "patch_request" else "concrete_file_operations"
            concrete = [{"action": "create_file" if actions == ["write_files"] else "apply_patch", "target_path": primary_target}] if primary_target else []
            project_plan = {}
            patch_plan = self._patch_plan(primary_target, text) if op_type == "patch_request" else {}
            shell_plan = {}
            expected = ["patch_result", "validation_result"] if op_type == "patch_request" else ["filesystem_operation", "validation_result"]
            if op_type == "patch_request" and not self._patch_plan_has_concrete_operations(patch_plan):
                prior_plan = self._latest_session_patch_plan(
                    session_id=session_id,
                    workspace=workspace or base_path,
                )
                if prior_plan:
                    patch_plan = prior_plan["patch_plan"]
                    target_paths = prior_plan["target_paths"] or target_paths
                    primary_target = target_paths[0] if target_paths else primary_target
                    base_path = prior_plan["workspace"] or base_path
                    execution_intent = prior_plan.get("execution_intent") or {}
                    executable_patch_plan = prior_plan.get("executable_patch_plan") or {}
                    execution_preview = prior_plan.get("execution_preview") or {}
                    concrete = [
                        {"action": "apply_patch", "target_path": target}
                        for target in target_paths
                    ]

        if "shell_plan" not in locals():
            shell_plan = {}
        executable_plan_ref = None
        if (
            plan_kind == "patch_plan"
            and isinstance(executable_patch_plan, dict)
            and str(executable_patch_plan.get("status") or "") == "complete"
        ):
            executable_plan_ref = str(executable_patch_plan.get("executable_plan_id") or "") or None
        if executable_plan_ref is None and self._has_executable_payload(
            plan_kind,
            concrete,
            project_plan,
            patch_plan,
            target_paths,
            shell_plan,
            executable_patch_plan=executable_patch_plan,
        ):
            executable_plan_ref = f"canonical_plan_{uuid4().hex}:{plan_kind}"
        workspace_path = base_path or (Path(primary_target).parent.as_posix() if primary_target else None)
        source_message_id = f"source_message_{uuid4().hex}"
        context_ref = f"context_{uuid4().hex}"
        discovery_ref = f"discovery_{uuid4().hex}" if workspace_path else None
        analysis_ref = f"analysis_{uuid4().hex}" if self._project_plan_has_analysis(project_plan) else None
        validation_plan = self._validation_plan(plan_kind, target_paths, expected)
        rollback_plan = self._rollback_plan(actions, target_paths)
        plan_payload = {
            "concrete_file_operations": concrete,
            "project_generation_plan": project_plan,
            "patch_plan": patch_plan,
            "execution_intent": execution_intent,
            "executable_patch_plan": executable_patch_plan,
            "execution_preview": execution_preview,
            "shell_plan": shell_plan,
            "validation_plan": validation_plan,
            "rollback_plan": rollback_plan,
        }
        return {
            "operation_type": op_type,
            "requested_actions": actions,
            "contract_type": contract_type,
            "runtime_profile": runtime_profile,
            "target_paths": target_paths,
            "primary_target_path": primary_target,
            "workspace_path": workspace_path,
            "executable_plan_ref": executable_plan_ref,
            "plan_kind": plan_kind,
            "expected_outputs": expected,
            "source_message_id": source_message_id,
            "context_ref": context_ref,
            "discovery_ref": discovery_ref,
            "analysis_ref": analysis_ref,
            "validation_plan": validation_plan,
            "rollback_plan": rollback_plan,
            "plan_payload": plan_payload,
            "concrete_file_operations": concrete,
            "project_generation_plan": project_plan,
            "patch_plan": patch_plan,
            "execution_intent": execution_intent,
            "executable_patch_plan": executable_patch_plan,
            "execution_preview": execution_preview,
            "shell_plan": shell_plan,
            "capabilities_required": self._capabilities(actions),
            "contract_preview": {
                "contract_type": contract_type,
                "runtime_profile": runtime_profile,
                "target_paths": target_paths,
                "executable_plan_ref": executable_plan_ref,
                "expected_outputs": expected,
                "plan_kind": plan_kind,
                "target_files": target_paths,
                "validation_plan": validation_plan,
                "rollback_plan": rollback_plan,
                "context_ref": context_ref,
                "discovery_ref": discovery_ref,
                "analysis_ref": analysis_ref,
                "patch_plan_id": patch_plan.get("patch_plan_id") if isinstance(patch_plan, dict) else None,
                "execution_intent_id": execution_intent.get("intent_id") if isinstance(execution_intent, dict) else None,
                "executable_patch_plan_id": executable_patch_plan.get("executable_plan_id") if isinstance(executable_patch_plan, dict) else None,
                "execution_preview_id": execution_preview.get("execution_preview_id") if isinstance(execution_preview, dict) else None,
                "execution_preview_status": execution_preview.get("status") if isinstance(execution_preview, dict) else None,
                "execution_preview_completeness": execution_preview.get("completeness") if isinstance(execution_preview, dict) else None,
            },
        }

    def _latest_session_patch_plan(
        self,
        *,
        session_id: str | None,
        workspace: str | None,
    ) -> dict[str, Any] | None:
        context = self.readonly_artifact_runtime.latest_patch_plan_context(
            session_id=session_id,
            workspace=workspace,
        )
        if not context:
            return None
        plan = context.get("patch_plan")
        if not isinstance(plan, dict):
            return None
        target_paths = [
            str(item)
            for item in context.get("target_paths", [])
            if item
        ]
        execution_plan = self._execution_patch_plan_from_canonical(plan)
        if not self._patch_plan_has_concrete_operations(execution_plan):
            return None
        compiled_intent, compiled_plan, compiled_preview = self.execution_preview_compiler.compile(
            repair_proposal=plan.get("repair_proposal"),
            patch_plan=execution_plan,
            workspace_hint=str(context.get("workspace") or workspace or ""),
        )
        return {
            "patch_plan": execution_plan,
            "target_paths": target_paths,
            "workspace": context.get("workspace"),
            "execution_intent": compiled_intent.model_dump(mode="json"),
            "executable_patch_plan": compiled_plan.model_dump(mode="json"),
            "execution_preview": compiled_preview.model_dump(mode="json"),
        }

    def _execution_patch_plan_from_canonical(self, plan: dict[str, Any]) -> dict[str, Any]:
        affected = [item for item in plan.get("affected_files", []) or [] if isinstance(item, dict)]
        hunks = [item for item in plan.get("hunks", []) or [] if isinstance(item, dict)]
        proposal = plan.get("diff_proposal") if isinstance(plan.get("diff_proposal"), dict) else {}
        diff = proposal.get("diff") if isinstance(proposal.get("diff"), dict) else {}
        diff_ref = str(proposal.get("proposal_id") or "")
        diff_text = str(diff.get("diff_text") or "")
        files_to_modify = []
        operations = []
        for file in affected:
            target = file.get("normalized_path") or file.get("path") or file.get("relative_path")
            relative = file.get("relative_path") or file.get("path")
            if not target:
                continue
            file_hunks = [
                hunk
                for hunk in hunks
                if str(hunk.get("file_path") or "").replace("\\", "/").strip("/")
                == str(relative or target).replace("\\", "/").strip("/")
            ]
            entry = {
                "path": str(target),
                "relative_path": str(relative or target),
                "diff_ref": diff_ref,
                "hunks": file_hunks,
            }
            files_to_modify.append(entry)
            operations.append(
                {
                    "operation": "apply_patch_after_approval",
                    "target_path": str(target),
                    "relative_path": str(relative or target),
                    "diff_ref": diff_ref,
                    "hunks": file_hunks,
                }
            )
        return {
            "patch_plan_id": plan.get("plan_id"),
            "source": "canonical_patch_plan",
            "workspace": plan.get("workspace"),
            "files_to_modify": files_to_modify,
            "patch_operations": operations,
            "affected_files": affected,
            "hunks": hunks,
            "diff_ref": diff_ref,
            "diff_text": diff_text,
            "validation": plan.get("validation") if isinstance(plan.get("validation"), dict) else {},
            "rollback_notes": list(plan.get("rollback_notes") or []),
            "risk": plan.get("risk") if isinstance(plan.get("risk"), dict) else {},
        }

    def _has_executable_payload(
        self,
        plan_kind: str,
        concrete: list[dict[str, Any]],
        project_plan: dict[str, Any],
        patch_plan: dict[str, Any],
        target_paths: list[str],
        shell_plan: dict[str, Any] | None = None,
        executable_patch_plan: dict[str, Any] | None = None,
    ) -> bool:
        if plan_kind == "project_generation_plan":
            if not any(project_plan.get(key) for key in ("directories_to_create", "files_to_create", "files_to_modify", "generation_steps", "validation_steps")):
                return False
            return self._project_generation_plan_has_writable_content(project_plan)
        if plan_kind == "patch_plan":
            if isinstance(executable_patch_plan, dict) and str(executable_patch_plan.get("status") or "") == "complete":
                return True
            return self._patch_plan_has_concrete_operations(patch_plan)
        if plan_kind == "concrete_file_operations":
            return bool(concrete)
        if plan_kind == "shell_plan":
            shell = shell_plan or {}
            return bool(target_paths and (shell.get("command") or shell.get("argv")))
        return False

    def _patch_plan_has_concrete_operations(self, patch_plan: dict[str, Any]) -> bool:
        entries: list[Any] = []
        for key in ("files_to_create", "files_to_modify", "patch_operations", "operations"):
            value = patch_plan.get(key) if isinstance(patch_plan, dict) else None
            if isinstance(value, list):
                entries.extend(value)
        if patch_plan.get("diff_ref") if isinstance(patch_plan, dict) else False:
            return bool(entries) and any(self._patch_target_is_file_like(item) for item in entries)
        return any(self._concrete_patch_entry(item) for item in entries)

    def _concrete_patch_entry(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        if not self._patch_target_is_file_like(item):
            return False
        return any(
            item.get(key)
            for key in (
                "content",
                "text",
                "body",
                "lines",
                "diff",
                "patch",
                "diff_ref",
                "hunks",
                "original",
                "replacement",
            )
        )

    def _patch_target_is_file_like(self, item: Any) -> bool:
        if not isinstance(item, dict):
            return False
        target = item.get("path") or item.get("target_path") or item.get("file_path") or item.get("relative_path")
        if not target:
            return False
        text = str(target).strip().strip('"`')
        if not text or text.endswith(("/", "\\")):
            return False
        try:
            path = Path(text)
            if path.exists() and path.is_dir():
                return False
        except (OSError, ValueError):
            return False
        return True

    def _project_generation_plan(self, target: str | None, text: str) -> dict[str, Any]:
        if not target:
            return {}
        template_files = self._project_template_files(target, text)
        android_jvm_target_files = self._android_jvm_target_config_files(target, text)
        android_sdk_config_files = self._android_sdk_config_files(target, text)
        if android_jvm_target_files:
            files_to_create = []
            files_to_modify = [
                {
                    "relative_path": relative_path,
                    "target_path": str((Path(target) / relative_path).resolve(strict=False)),
                    "purpose": "android_gradle_jvm_target_alignment",
                    "content": content,
                    "encoding": "utf-8",
                    "overwrite": True,
                }
                for relative_path, content in sorted(android_jvm_target_files.items())
            ]
            generation_steps = [
                "inspect_workspace_readonly",
                "align_android_java_kotlin_jvm_targets_after_approval",
                "publish_validation_result",
            ]
            validation_steps = [
                "no_write_before_approval",
                "android_gradle_file_exists",
                "java_kotlin_jvm_targets_aligned",
                "validate_expected_outputs",
            ]
            analysis_summary = {
                "kind": "android_gradle_build_failure_recovery",
                "reason_code": "android_kotlin_java_jvm_target_mismatch",
            }
        elif android_sdk_config_files:
            files_to_create = [
                {
                    "relative_path": relative_path,
                    "target_path": str((Path(target) / relative_path).resolve(strict=False)),
                    "purpose": "android_sdk_local_properties_config",
                    "content": content,
                    "encoding": "utf-8",
                    "overwrite": True,
                }
                for relative_path, content in sorted(android_sdk_config_files.items())
            ]
            generation_steps = [
                "inspect_workspace_readonly",
                "write_android_sdk_local_properties_after_approval",
                "publish_validation_result",
            ]
            validation_steps = [
                "no_write_before_approval",
                "local_properties_exists",
                "sdk_dir_present",
                "validate_expected_outputs",
            ]
            files_to_modify = []
            analysis_summary = {
                "kind": "android_gradle_build_failure_recovery",
                "reason_code": "android_sdk_location_missing",
            }
        elif template_files:
            files_to_create = [
                {
                    "relative_path": relative_path,
                    "target_path": str((Path(target) / relative_path).resolve(strict=False)),
                    "purpose": "generated_project_template_file",
                    "content": content,
                    "encoding": "utf-8",
                    "overwrite": True,
                }
                for relative_path, content in sorted(template_files.items())
            ]
            generation_steps = [
                "inspect_workspace_readonly",
                "create_template_project_files_after_approval",
                "publish_validation_result",
            ]
            validation_steps = [
                "no_write_before_approval",
                "generated_files_exist",
                "android_project_structure_present",
                "validate_expected_outputs",
            ]
            files_to_modify = []
            analysis_summary = None
        else:
            content = self._project_generation_plan_content(target, text)
            bootstrap_path = "AIpinho_PROJECT_BOOTSTRAP_PLAN.md"
            files_to_create = [
                {
                    "relative_path": bootstrap_path,
                    "target_path": str((Path(target) / bootstrap_path).resolve(strict=False)),
                    "purpose": "governed_project_bootstrap_plan",
                    "content": content,
                    "encoding": "utf-8",
                    "overwrite": True,
                }
            ]
            generation_steps = [
                "inspect_workspace_readonly",
                "create_or_update_project_files_after_approval",
                "publish_validation_result",
            ]
            validation_steps = ["no_write_before_approval", "validate_expected_outputs"]
            files_to_modify = []
            analysis_summary = None
        return {
            "target_workspace": target,
            "directories_to_create": [{"path": target, "purpose": "project_bootstrap_target"}],
            "files_to_create": files_to_create,
            "files_to_modify": files_to_modify,
            "generation_steps": generation_steps,
            "validation_steps": validation_steps,
            "expected_outputs": ["project_generation", "validation_result"],
            "prompt_excerpt": text[:500],
            "analysis_summary": analysis_summary,
        }

    def _project_template_files(self, target: str, text: str) -> dict[str, str]:
        normalized = str(text or "").casefold()
        wants_mobile_game = any(marker in normalized for marker in ("jogo mobile", "mobile game", "jogo android", "android game"))
        wants_android = any(marker in normalized for marker in ("android", "kotlin", "gradle", "apk"))
        wants_game = any(marker in normalized for marker in ("jogo", "game"))
        if not (wants_mobile_game or (wants_android and wants_game)):
            return {}
        project_name = Path(target).name or "GeneratedMobileGame"
        package_name = self._android_package_name(project_name)
        return android_kotlin_simple_game_template(project_name=project_name, package_name=package_name)

    def _android_sdk_config_files(self, target: str, text: str) -> dict[str, str]:
        normalized = str(text or "").casefold()
        has_android_sdk_signal = any(
            marker in normalized
            for marker in (
                "sdk location not found",
                "sdk.dir",
                "local.properties",
                "android sdk",
                "android_home",
            )
        )
        if not has_android_sdk_signal:
            return {}
        sdk_path = self._first_path_after_labels(
            text,
            ("android sdk local conhecido", "android sdk", "sdk.dir", "sdk", "android_home"),
        )
        if not sdk_path:
            return {}
        safe_sdk_path = str(Path(sdk_path)).replace("\\", "/")
        return {
            "local.properties": (
                "# Generated by AIpinho governed Android SDK recovery.\n"
                "# Local machine path; do not commit secrets here.\n"
                f"sdk.dir={safe_sdk_path}\n"
            )
        }

    def _android_jvm_target_config_files(self, target: str, text: str) -> dict[str, str]:
        normalized = str(text or "").casefold()
        has_jvm_target_signal = any(
            marker in normalized
            for marker in (
                "inconsistent jvm-target",
                "inconsistent jvm target",
                "jvm-target compatibility",
                "jvm target compatibility",
                "compiledebugkotlin",
                "compiledebugjavawithjavac",
            )
        )
        if not has_jvm_target_signal:
            return {}
        gradle_file = Path(target) / "app" / "build.gradle.kts"
        if not gradle_file.exists():
            return {}
        content = gradle_file.read_text(encoding="utf-8")
        updated = self._with_android_jvm_target_alignment(content)
        if updated == content:
            return {}
        return {"app/build.gradle.kts": updated}

    def _with_android_jvm_target_alignment(self, content: str) -> str:
        updated = content
        if "compileOptions" not in updated:
            updated = self._insert_before_last_android_brace(
                updated,
                (
                    "    compileOptions {\n"
                    "        sourceCompatibility = JavaVersion.VERSION_17\n"
                    "        targetCompatibility = JavaVersion.VERSION_17\n"
                    "    }\n"
                ),
            )
        if "kotlinOptions" not in updated:
            updated = self._insert_before_last_android_brace(
                updated,
                (
                    "    kotlinOptions {\n"
                    '        jvmTarget = "17"\n'
                    "    }\n"
                ),
            )
        return updated

    def _insert_before_last_android_brace(self, content: str, block: str) -> str:
        index = content.rfind("}")
        if index == -1:
            suffix = "\n" if content and not content.endswith("\n") else ""
            return f"{content}{suffix}{block}"
        prefix = content[:index].rstrip()
        suffix = content[index:]
        return f"{prefix}\n{block}{suffix}"

    def _android_package_name(self, project_name: str) -> str:
        slug = re.sub(r"[^a-z0-9_]+", "_", str(project_name or "").casefold()).strip("_")
        slug = re.sub(r"_+", "_", slug) or "generated_mobile_game"
        if slug[0].isdigit():
            slug = f"app_{slug}"
        return f"br.com.aipinho.generated.{slug}"

    def _project_generation_plan_has_writable_content(self, plan: dict[str, Any]) -> bool:
        file_entries = [
            *self._list(plan.get("files_to_create")),
            *self._list(plan.get("files_to_modify")),
        ]
        if not file_entries:
            return bool(self._list(plan.get("directories_to_create")))
        for entry in file_entries:
            if not isinstance(entry, dict):
                return False
            value = entry.get("content") or entry.get("text") or entry.get("body")
            lines = entry.get("lines")
            if value is None and not (isinstance(lines, list) and lines):
                return False
        return True

    def _project_plan_has_analysis(self, plan: dict[str, Any]) -> bool:
        analysis = plan.get("analysis_summary") if isinstance(plan, dict) else None
        return isinstance(analysis, dict) and bool(analysis.get("reason_code") or analysis.get("kind"))

    def _list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _project_generation_plan_content(self, target: str, text: str) -> str:
        prompt_excerpt = str(text or "").strip()[:1200]
        return (
            "# AIpinho Governed Project Bootstrap Plan\n\n"
            "Status: approved_execution_plan\n\n"
            f"Target workspace: {target}\n\n"
            "Generated by: AIpinho canonical governance lifecycle\n\n"
            "Purpose:\n"
            "- Record the approved bootstrap intent before mutable project work.\n"
            "- Keep execution auditable, reversible and validation-aware.\n\n"
            "Execution notes:\n"
            "- This file is produced only after approval.\n"
            "- Source/workload folders must remain read-only unless a later approved plan explicitly targets them.\n"
            "- Further project files require concrete file operations, validation outputs and speaker-truth checks.\n\n"
            "Original request excerpt:\n"
            "```text\n"
            f"{prompt_excerpt}\n"
            "```\n"
        )

    def _patch_plan(self, target: str | None, text: str) -> dict[str, Any]:
        if not target:
            return {}
        return {
            "files_to_modify": [{"path": target, "purpose": "patch_target"}],
            "patch_operations": [{"operation": "apply_patch_after_approval", "target_path": target}],
            "validation_steps": ["diff_matches_preview", "validation_result"],
            "prompt_excerpt": text[:500],
        }

    def _validation_plan(self, plan_kind: str, target_paths: list[str], expected_outputs: list[str]) -> dict[str, Any]:
        return {
            "kind": plan_kind,
            "target_paths": target_paths,
            "checks": ["target_paths_match_preview", "expected_outputs_present", "no_unapproved_side_effects"],
            "expected_outputs": expected_outputs,
        }

    def _rollback_plan(self, actions: list[str], target_paths: list[str]) -> dict[str, Any]:
        return {
            "strategy": "record_pre_state_and_revert_on_failure",
            "actions": actions,
            "target_paths": target_paths,
        }

    def _shell_plan(self, workspace: str | None, text: str) -> dict[str, Any]:
        command = self._extract_shell_command(text)
        if not workspace or not command:
            return {}
        category = self._shell_category(command)
        return {
            "command": command,
            "cwd": workspace,
            "shell_category": category,
            "timeout_seconds": 240 if category == "build_shell" else 120,
            "expected_exit_code": 0,
            "validation_steps": ["shell_exit_code_matches_expected", "stdout_stderr_sanitized"],
        }

    def _extract_shell_command(self, text: str) -> str | None:
        source = str(text or "")
        command_markers = ("gradle", "gradlew", "npm", "pytest", "python", "java", "adb", "where", "cmd")
        labeled_command = self._command_after_labeled_command(source, command_markers)
        if labeled_command:
            return labeled_command
        explicit_match = re.search(
            r"(?i)\b(?:execute|executar|rode|rodar|run)\s+(.+?)(?:\s+(?:em|no|na|dentro)\b|[.;\n\r]|$)",
            source,
        )
        if explicit_match:
            candidate = explicit_match.group(1).strip().strip('"`')
            if self._looks_like_shell_command(candidate, command_markers):
                return candidate
        if self._has_failed_command_evidence_without_explicit_command(source):
            return None
        for quoted in re.findall(r'["“](.+?)["”]', source):
            candidate = quoted.strip()
            quote_start = source.find(quoted)
            quote_context = source[
                max(0, quote_start - 100 if quote_start >= 0 else 0) :
                min(len(source), quote_start + len(quoted) + 100 if quote_start >= 0 else len(source))
            ].casefold()
            if self._contains_shell_failure_marker(quote_context):
                continue
            if self._looks_like_shell_command(candidate, command_markers):
                return candidate
        match = re.search(
            r"(?i)\b(?:execute|executar|rode|rodar|run)\s+(.+?)(?:\s+(?:em|no|na|dentro)\b|[.;\n\r]|$)",
            source,
        )
        if match:
            candidate = match.group(1).strip().strip('"`')
            if self._looks_like_shell_command(candidate, command_markers):
                return candidate
        normalized = source.casefold()
        if "assembledebug" in normalized:
            return "gradlew.bat assembleDebug" if "gradlew" in normalized else "gradle assembleDebug"
        if "npm test" in normalized:
            return "npm test"
        if "pytest" in normalized:
            return "pytest"
        return None

    def _command_after_labeled_command(self, source: str, command_markers: tuple[str, ...]) -> str | None:
        match = re.search(
            r"(?im)^\s*(?:comando(?:\s+(?:governado|read-only|readonly))?|command)\s*:\s*(.+?)\s*$",
            source,
        )
        if not match:
            return None
        candidate = match.group(1).strip().strip("`")
        if (candidate.startswith('"') and candidate.endswith('"')) or (
            candidate.startswith("'") and candidate.endswith("'")
        ):
            candidate = candidate[1:-1].strip()
        candidate = candidate.replace('""', '"')
        return candidate if self._looks_like_shell_command(candidate, command_markers) else None

    def _has_failed_command_evidence_without_explicit_command(self, source: str) -> bool:
        pattern = r"(?i)\b(?:execute|executar|rode|rodar|run)(?![A-Za-z0-9_])\s+"
        for match in re.finditer(pattern, source):
            prefix = source[max(0, match.start() - 12) : match.start()].casefold()
            if not any(marker in prefix for marker in ("nao ", "nÃ£o ", "nunca ", "sem ")):
                return False
        return self._contains_shell_failure_marker(source.casefold())

    @staticmethod
    def _contains_shell_failure_marker(normalized: str) -> bool:
        return any(
            marker in normalized
            for marker in (
                "falhou",
                "falha",
                "failed",
                "exit_code",
                "exit code",
                "file not found",
                "not found",
                "nao encontrado",
                "nÃ£o encontrado",
                "nao foi encontrado",
                "nÃ£o foi encontrado",
                "nao existe",
                "nÃ£o existe",
            )
        )

    def _shell_category(self, command: str) -> str:
        normalized = str(command or "").casefold()
        first_token = re.split(r"\s+", normalized, maxsplit=1)[0].strip("`'\"")
        executable = Path(first_token).name.casefold()
        readonly_executables = {"where", "where.exe", "dir", "ls", "type", "cat", "get-command"}
        readonly_cmd = normalized.startswith(("cmd /c where", "cmd /c dir", "cmd /c if ", "cmd /c echo"))
        readonly_version = any(marker in normalized for marker in ("java -version", "gradle -v", "gradlew -v"))
        if executable in readonly_executables or readonly_cmd or readonly_version:
            return "readonly_shell"
        if executable in {"gradle", "gradle.bat", "gradlew", "gradlew.bat"} or any(marker in normalized for marker in ("assemble", " build", "build ")):
            return "build_shell"
        if any(marker in normalized for marker in ("test", "pytest")):
            return "test_shell"
        return "unknown_shell"

    def _looks_like_shell_command(self, candidate: str, command_markers: tuple[str, ...]) -> bool:
        candidate = " ".join(str(candidate or "").strip().split())
        if not candidate:
            return False
        path_like = bool(re.search(r"[a-z]:[\\/]", candidate.casefold())) or "\\" in candidate or "/" in candidate
        first_token = re.split(r"\s+", candidate.casefold(), maxsplit=1)[0].strip("`'\"")
        if path_like and first_token not in command_markers:
            executable_name = Path(first_token).name.casefold()
            return executable_name.endswith((".bat", ".cmd", ".exe"))
        if first_token in command_markers:
            return True
        return bool(re.search(r"\b(?:gradlew|gradle|npm|pytest|python|java|adb|where|cmd)\b\s+\S+", candidate.casefold()))

    def _base_response(
        self,
        request: ChatRequest,
        *,
        status: str,
        operation_type: str,
        message_type: str,
        message: str,
        intent: dict[str, Any] | None = None,
        policy: dict[str, Any] | None = None,
        actions: list[str] | None = None,
        contract_preview: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
        task_draft_id: str | None = None,
        preview_id: str | None = None,
        approval_id: str | None = None,
        next_actions: list[ChatNextAction] | None = None,
        requires_user_action: bool = False,
    ) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_{uuid4().hex}",
            session_id=request.session_id,
            task_draft_id=task_draft_id,
            preview_id=preview_id,
            approval_id=approval_id,
            operation_id=f"chatop_{uuid4().hex}",
            operation_type=operation_type,
            message_type=message_type,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            message=message,
            intent=intent or {},
            policy=policy or {},
            actions=actions or [],
            contract_preview=contract_preview or {},
            warnings=list(dict.fromkeys(warnings or [])),
            next_actions=next_actions or [],
            requires_user_action=requires_user_action,
            is_final_answer=status not in {"pending_approval", "preview"},
            grounded=True,
            model_used="canonical_governance_lifecycle",
            real_inference=False,
            fallback_used=False,
        )

    def _attach_lifecycle(self, response: ChatResponse, snapshot: GovernanceLifecycleSnapshot) -> ChatResponse:
        policy = dict(response.policy)
        policy["canonical_lifecycle"] = {
            "lifecycle_id": snapshot.lifecycle_id,
            "state": snapshot.state.value,
            "reason_code": snapshot.reason_code.value,
            "permission": snapshot.policy.permission.value,
            "approval_gate_status": snapshot.approval_gate.status,
            "approval_id": snapshot.approval_gate.approval_id,
            "preview_id": snapshot.approval_gate.preview_id,
            "draft_id": snapshot.approval_gate.draft_id,
        }
        return response.model_copy(update={"policy": policy, "governance_lifecycle": snapshot.model_dump()})

    def _workspace_from_request(self, request: ChatRequest) -> str | None:
        if request.context and request.context.active_workspace:
            return request.context.active_workspace
        paths = self._extract_paths(request.message)
        return paths[-1] if paths else None

    def _readonly_analysis_workspace(self, text: str, fallback: str | None) -> str | None:
        paths = self._extract_paths(text)
        if not paths:
            return fallback
        normalized = str(text or "").casefold()
        labeled_source = self._first_path_after_labels(text, ("fonte", "source", "workload", "projeto fonte", "projeto", "project"))
        if labeled_source:
            return labeled_source
        if any(marker in normalized for marker in ("workload read-only", "fonte read-only", "source read-only", "source_readonly")):
            return paths[0]
        if len(paths) > 1 and any(marker in normalized for marker in ("workspace futuro", "target futuro", "alvo futuro", "workspace alvo futuro")):
            return paths[0]
        return fallback or paths[0]

    def _target_workspace_from_request(self, text: str, *, source_workspace: str | None) -> str | None:
        paths = self._extract_paths(text)
        if not paths:
            return None
        normalized = str(text or "").casefold()
        labeled_target = self._first_path_after_labels(text, ("alvo", "target", "destino", "workspace alvo"))
        if labeled_target and labeled_target != source_workspace:
            return labeled_target
        if len(paths) > 1 and any(marker in normalized for marker in ("target", "alvo", "futuro", "destino")):
            for path in reversed(paths):
                if path != source_workspace:
                    return path
        return None

    def _looks_like_readonly_project_plan(self, text: str) -> bool:
        normalized = str(text or "").casefold()
        has_plan_signal = any(
            marker in normalized
            for marker in (
                "plano governado",
                "plano tecnico",
                "plano técnico",
                "preview textual",
                "plano de acao",
                "plano de ação",
                "planejamento",
                "roadmap",
                "sprint roadmap",
                "technical project plan",
                "architecture map",
                "mapa arquitetural",
                "entrypoints",
                "componentes",
                "modulos",
                "módulos",
                "game loop",
                "estado atual",
                "estado desejado",
                "reconstru",
                "arquivos provaveis",
                "arquivos prováveis",
                "rollback",
                "criterios de validacao",
                "critérios de validação",
                "decision log",
                "proximo passo",
                "próximo passo",
                "validacoes",
                "validações",
            )
        )
        has_no_side_effect_signal = any(
            marker in normalized
            for marker in (
                "read-only",
                "readonly",
                "somente leitura",
                "somente read-only",
                "apenas leitura",
                "modo read-only",
                "nao escreva",
                "não escreva",
                "nao escrever",
                "não escrever",
                "nao modificar",
                "não modificar",
                "sem escrita",
                "nao aplique patch",
                "não aplique patch",
                "nao executar patch",
                "não executar patch",
                "nao rode shell",
                "não rode shell",
                "nao executar shell",
                "não executar shell",
                "nao executar build",
                "não executar build",
                "nao criar arquivo",
                "não criar arquivo",
                "nao crie arquivo",
                "não crie arquivo",
                "nao criar artifact",
                "não criar artifact",
                "nao criar artifacts",
                "não criar artifacts",
                "nao crie approval",
                "não crie approval",
                "nao criar approvalrequest",
                "não criar approvalrequest",
                "nao crie approvalrequest",
                "não crie approvalrequest",
                "nao criar taskpreview",
                "não criar taskpreview",
                "nao crie taskpreview",
                "não crie taskpreview",
                "sem criar preview",
                "sem side effects",
            )
        )
        return has_plan_signal and has_no_side_effect_signal

    def _extract_paths(self, text: str) -> list[str]:
        paths = [item.value.rstrip("\\") for item in PathExtractionService().extract(text or "")]
        if paths:
            return list(dict.fromkeys(paths))
        paths: list[str] = []
        for match in self._WINDOWS_PATH_RE.finditer(text or ""):
            value = self._clean_path_candidate(match.group("path"))
            value = value.replace("/", "\\").rstrip("\\")
            if value:
                paths.append(value)
        return list(dict.fromkeys(paths))

    def _first_path_after_labels(self, text: str, labels: tuple[str, ...]) -> str | None:
        source = str(text or "")
        for label in labels:
            pattern = r"(?<![A-Za-z0-9_])" + re.escape(label) + r"(?![A-Za-z0-9_])"
            for match in re.finditer(pattern, source, flags=re.IGNORECASE):
                segment = source[match.end() : match.end() + 500]
                paths = self._extract_paths(segment)
                if paths:
                    return paths[0]
        return None

    def _clean_path_candidate(self, value: str) -> str:
        text = str(value or "").strip()
        text = re.split(
            r"\s+(?:workspace|workload|fonte|source|target|alvo|futuro|comece|nao|não|retorne|responda|faca|faça|crie|implemente|utilize|use|objetivo|esperado|expected)\b",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        return text.strip().strip(" .,;:)'\"`")

    def _extract_named_container(self, text: str) -> str | None:
        match = self._NAMED_CONTAINER_RE.search(text or "")
        if not match:
            return None
        prefix = str(text or "")[max(0, match.start() - 140) : match.start()].casefold()
        if not any(
            marker in prefix
            for marker in (
                "crie",
                "criar",
                "cria",
                "inicie",
                "iniciar",
                "implemente",
                "implementar",
                "bootstrap",
                "mkdir",
                "nova",
                "novo",
            )
        ):
            return None
        name = match.group("name").strip().strip(" .,:;\"'`")
        if not name or re.search(r"[\\/<>|:*?]", name):
            return None
        return name

    def _target_path(self, base_path: str | None, folder_name: str | None) -> str | None:
        if folder_name and base_path:
            return str(Path(base_path) / folder_name).replace("/", "\\")
        return base_path

    def _capabilities(self, actions: list[str]) -> list[str]:
        capabilities: list[str] = []
        if any(action in {"write_files", "create_directory"} for action in actions):
            capabilities.append("write_workspace")
        if "apply_patch" in actions:
            capabilities.append("apply_patch")
        if "run_command" in actions:
            capabilities.append("governed_shell")
        return capabilities
