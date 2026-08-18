from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from aipinho.schemas.artifacts.workspace_readonly_audit_report import WorkspaceReadonlyAuditReportRequest
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.workspace_readonly_audit_report_service import WorkspaceReadonlyAuditReportService
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.chat_operation_router_service import ChatOperationRouterService
from aipinho.services.chat.chat_permission_grant_service import ChatPermissionGrantService
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.chat.governed_write_chat_service import GovernedWriteChatService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.governance.operation_contract_service import OperationContractService
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore


class FakeShellRunner:
    def run(self, argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


class FakeReadonlyResolver:
    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, workspace_id=None, path_ref=None, access="read"):
        return SimpleNamespace(
            allowed=True,
            workspace_id="source",
            workspace_role="target_mutable",
            reason_code=None,
            root_path_sanitized=str(self.root),
            resolved_path_sanitized=str(self.root),
        )


def _config_root(tmp_path: Path) -> tuple[Path, Path]:
    target = tmp_path / "target"
    target.mkdir()
    config_root = tmp_path / "config"
    (config_root / "agents").mkdir(parents=True)
    for filename in ["tool_gateway_registry.yaml", "tool_gateway_policy.yaml"]:
        (config_root / "agents" / filename).write_text(Path("config/agents", filename).read_text(encoding="utf-8"), encoding="utf-8")
    (config_root / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"""
version: 1
workspaces:
  - workspace_id: target
    root: {target}
    role: target_mutable
    enabled: true
""",
        encoding="utf-8",
    )
    return config_root, target


def _approval_scoped_chat_service(tmp_path: Path) -> tuple[ChatService, Path, ApprovalService]:
    config_root, target = _config_root(tmp_path)
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(config_root / "agents" / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(config_root / "agents" / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(config_root / "agents" / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        shell_runner=FakeShellRunner(),
    )
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_service = TaskPreviewService(store=TaskPreviewStore(tmp_path / "previews"), draft_store=draft_store)
    approval_service = ApprovalService(
        store=ApprovalStore(tmp_path / "approvals"),
        preview_service=preview_service,
        draft_store=draft_store,
    )
    governed_write = GovernedWriteChatService(
        kernel=kernel,
        tool_gateway=gateway,
        require_chat_write_approval=True,
        draft_store=draft_store,
        preview_service=preview_service,
        approval_service=approval_service,
    )
    service = ChatService(governed_write_service=governed_write, approval_service=approval_service)
    return service, target, approval_service


def _project_generation_chat_service(tmp_path: Path) -> tuple[ChatService, Path, ApprovalService]:
    workspace = tmp_path / "project"
    workspace.mkdir()
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        f"""
schema_version: 1
workspaces:
  - workspace_id: project
    root_path: {workspace}
    role: target_mutable
    permissions:
      read_file: allowed
      list_files: allowed
      create_file: ask
      modify_file: ask
      apply_patch: ask
""",
        encoding="utf-8",
    )
    matrix = WorkspacePermissionMatrixService(registry).load()
    draft_store = TaskDraftStore(tmp_path / "project_drafts")
    preview_service = TaskPreviewService(store=TaskPreviewStore(tmp_path / "project_previews"), draft_store=draft_store)
    approval_service = ApprovalService(
        store=ApprovalStore(tmp_path / "project_approvals"),
        preview_service=preview_service,
        draft_store=draft_store,
    )
    service = ChatService(
        task_draft_service=TaskContractDraftService(store=draft_store),
        task_preview_service=preview_service,
        approval_service=approval_service,
        operation_contract_service=OperationContractService(permission_matrix=matrix),
    )
    return service, workspace, approval_service


def test_ask_policy_creates_approval_not_blocked(tmp_path: Path) -> None:
    service, target, approval_service = _approval_scoped_chat_service(tmp_path)

    response = service.respond(
        ChatRequest(
            message="Crie o arquivo notes/summary.md no workspace alvo com conteudo 'ok'.",
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    assert response.status == "pending_approval"
    assert response.approval_id
    assert response.preview_id
    assert response.policy["approval_actions"] == ["write_files"]
    assert approval_service.get_approval(response.approval_id) is not None
    assert not (target / "notes" / "summary.md").exists()


def test_permission_phrase_creates_session_grant_not_config_change(tmp_path: Path) -> None:
    workspace = tmp_path / "target"
    workspace.mkdir()

    response = ChatPermissionGrantService().handle(
        session_id="chat_test",
        text=f"Dou permissao para criar e alterar arquivos durante esta tarefa em {workspace}",
    )

    assert response is not None
    assert response.status == "pending_approval"
    assert response.operation_type == "session_permission_grant"
    assert response.policy["grant_id"].startswith("grant_")
    assert response.operation_type != "config_permission_grant_preview"


def test_product_planning_readonly_not_permission_grant() -> None:
    response = ChatPermissionGrantService().handle(
        session_id="chat_test",
        text=(
            "Objetivo: responder somente com analise de produto, relatorio e plano de acao em sprints. "
            "Isto NAO e pedido para criar grant. Isto NAO e pedido para escrever arquivo. "
            "Classifique este pedido como: product_planning_readonly."
        ),
    )

    assert response is None


def test_negative_permission_terms_do_not_trigger_grant() -> None:
    response = ChatPermissionGrantService().handle(
        session_id="chat_test",
        text="Nao escrever arquivos, nao criar approval e nao criar grant; apenas liste riscos de governanca.",
    )

    assert response is None


def test_future_approval_checklist_not_permission_grant() -> None:
    response = ChatPermissionGrantService().handle(
        session_id="chat_test",
        text="Precisa approval de escrita no futuro: sim/nao. Responda como planning_readonly.",
    )

    assert response is None


def test_continue_from_preflight_starts_implementation_plan(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    report = workspace / "reports" / "preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Preflight\nSTATUS: PREFLIGHT_READY\n", encoding="utf-8")

    decision = ChatOperationRouterService().route(f"Continue a partir do preflight e implemente o MVP com base no relatorio {report}")

    assert decision.metadata["router_operation_type"] == "governed_project_rebuild"
    assert decision.metadata["phase_resume"]["completed_phase"] == "preflight"
    assert decision.metadata["phase_resume"]["next_phase"] == "implementation_plan"
    assert decision.workspace == str(workspace)


def test_phase_resume_persistent_chat_uses_canonical_preview_approval_flow(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    report = workspace / "reports" / "preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Preflight\nSTATUS: PREFLIGHT_READY\n", encoding="utf-8")
    prompt = f"Continue a partir do preflight e implemente o MVP com base no relatorio {report}"
    draft_store = TaskDraftStore(tmp_path / "canonical_drafts")
    preview_service = TaskPreviewService(
        store=TaskPreviewStore(tmp_path / "canonical_previews"),
        draft_store=draft_store,
    )
    approval_service = ApprovalService(
        store=ApprovalStore(tmp_path / "canonical_approvals"),
        preview_service=preview_service,
        draft_store=draft_store,
    )

    response = CanonicalPublicChatService(
        draft_store=draft_store,
        preview_service=preview_service,
        approval_service=approval_service,
    ).respond(
        ChatRequest(
            message=prompt,
            session_id="chat_phase_resume_test",
            context=ChatContext(surface="mobile", active_workspace=str(workspace)),
        ),
        source_channel="persistent_chat",
    )

    assert response.status == "pending_approval"
    assert response.approval_id
    assert response.preview_id
    assert response.policy["approval_required_for"] == ["write_files"]
    assert response.intent["intent_type"] in {"project_generation", "project_bootstrap"}
    assert approval_service.get_approval(response.approval_id) is not None


def test_continue_from_preflight_without_explicit_report_path_uses_existing_report(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    report = workspace / "reports" / "mobile_preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Preflight\nSTATUS: PREFLIGHT_READY\n", encoding="utf-8")

    decision = ChatOperationRouterService().route(
        "Continue a partir do preflight e implemente o MVP.",
        workspace_hint=str(workspace),
    )

    assert decision.metadata["router_operation_type"] == "governed_project_rebuild"
    assert decision.metadata["phase_resume"]["evidence_report_path"] == str(report)
    assert decision.metadata["phase_resume"]["next_phase"] == "implementation_plan"


def test_project_generation_policy_ask_creates_pending_approval(tmp_path: Path) -> None:
    service, workspace, approval_service = _project_generation_chat_service(tmp_path)
    decision = ChatOperationDecision(
        operation_id="chatop_project_generation_test",
        operation_type="project_generation",
        message_type="task_preview",
        confidence=0.9,
        workspace=str(workspace),
        primary_prompt="Crie um app simples neste workspace.",
        metadata={"requested_actions": ["create_project", "write_files"], "router_operation_type": "project_create"},
    )

    response = service._specific_operation_preview_response("chat_project_generation_test", decision)

    assert response.status == "pending_approval"
    assert response.approval_id
    assert response.preview_id
    assert response.policy["approval_required_for"] == ["write_files"]
    assert approval_service.get_approval(response.approval_id) is not None
    assert "PROJECT_GENERATION_PENDING_APPROVAL" in response.message
    assert not any(workspace.iterdir())


def test_studio_prompt_creates_task_preview_and_approval(tmp_path: Path) -> None:
    service, workspace, approval_service = _project_generation_chat_service(tmp_path)
    prompt = (
        f"AIpinho - Iniciar Projeto AIpinho Studio com governanca completa. "
        f"Workspace: {workspace}. Nao escreva arquivos agora. "
        "Crie somente blueprint, TaskPreview e ApprovalRequest."
    )
    decision = ChatOperationRouterService().route(prompt)

    response = service._specific_operation_preview_response("chat_studio_bootstrap_test", decision)

    assert decision.metadata["router_operation_type"] == "project_bootstrap"
    assert response.status == "pending_approval"
    assert response.approval_id
    assert response.preview_id
    assert response.task_id
    assert response.operation_id
    assert "PROJECT_BOOTSTRAP_PENDING_APPROVAL" in response.message
    approval = approval_service.get_approval(response.approval_id)
    assert approval is not None
    assert approval.status == "pending"
    assert "patch_result" not in approval.expected_outcomes
    assert "validation_result" not in approval.expected_outcomes
    assert "task_preview_result" in approval.expected_outcomes
    assert "approval_request_result" in approval.expected_outcomes
    assert not any(workspace.iterdir())


def test_no_patch_result_required_before_bootstrap_approval(tmp_path: Path) -> None:
    service, workspace, approval_service = _project_generation_chat_service(tmp_path)
    decision = ChatOperationRouterService().route(
        f"Iniciar projeto com safety check e diagnostico de approval. Workspace: {workspace}"
    )

    response = service._specific_operation_preview_response("chat_bootstrap_outcomes_test", decision)
    approval = approval_service.get_approval(response.approval_id)

    assert approval is not None
    assert approval.expected_outcomes == [
        "discovery_result",
        "blueprint_result",
        "task_preview_result",
        "approval_request_result",
    ]
    assert "patch_result" not in approval.expected_outcomes
    assert "validation_result" not in approval.expected_outcomes


def test_no_old_approval_reuse_requested_in_bootstrap_metadata() -> None:
    decision = ChatOperationRouterService().route(
        "AIpinho - Iniciar Projeto AIpinho Studio. Nao reutilize approvals antigos; crie novo ApprovalRequest."
    )

    assert decision.metadata["router_operation_type"] == "project_bootstrap"
    assert decision.metadata["do_not_reuse_old_approval"] is True


def test_create_folder_policy_ask_creates_approval(tmp_path: Path) -> None:
    service, workspace, approval_service = _project_generation_chat_service(tmp_path)
    prompt = f"Crie uma pasta chamada AIpinhoStudioMobile dentro de {workspace}."
    decision = ChatOperationRouterService().route(prompt)

    response = service._specific_operation_preview_response("chat_directory_create_test", decision)

    assert decision.operation_type == "filesystem_create_directory"
    assert decision.metadata["target_path"] == str(workspace / "AIpinhoStudioMobile").replace("/", "\\")
    assert response.status == "pending_approval"
    assert response.approval_id
    assert response.preview_id
    assert response.task_id
    assert response.policy["approval_required_for"] == ["create_directory"]
    approval = approval_service.get_approval(response.approval_id)
    assert approval is not None
    assert approval.status == "pending"
    assert approval.actions_requested == ["create_directory"]
    assert not (workspace / "AIpinhoStudioMobile").exists()


def test_implementation_request_does_not_route_to_workspace_readonly_audit_report(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    report = workspace / "reports" / "preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Preflight\n", encoding="utf-8")

    decision = ChatOperationRouterService().route(f"Leia o relatorio {report} e comece a escrever arquivos do MVP.")

    assert decision.metadata["router_operation_type"] == "governed_project_rebuild"
    assert decision.metadata["router_operation_type"] != "workspace_readonly_audit_report"
    assert decision.operation_type != "filesystem_read_file"


def test_preflight_existing_file_does_not_raise_file_exists(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    report = workspace / "reports" / "preflight.md"
    report.parent.mkdir(parents=True)
    report.write_text("# Existing\nworkspace_readonly_audit\n", encoding="utf-8")
    service = WorkspaceReadonlyAuditReportService(
        resolver=FakeReadonlyResolver(workspace),
        policy={"workspace_readonly_audit": {"enabled": True}},
    )

    result = service.execute(
        WorkspaceReadonlyAuditReportRequest(
            session_id="chat_test",
            operation_id="op_test",
            workspace_ref=str(workspace),
            prompt="Gere auditoria read-only",
            report_relative_path="reports/preflight.md",
            search_terms=["workspace_readonly_audit"],
        )
    )

    assert result.status == "completed"
    assert result.reason_code == "existing_report_reused"
    assert result.report_path == str(report)
    assert "existing_report_reused" in result.warnings


def test_list_pending_approvals_command_returns_visible_list(tmp_path: Path) -> None:
    service, _target, approval_service = _approval_scoped_chat_service(tmp_path)
    first = service.respond(
        ChatRequest(
            message="Crie o arquivo notes/summary.md no workspace alvo com conteudo 'ok'.",
            context=ChatContext(surface="api", active_workspace="target"),
        )
    )

    response = ChatApprovalCommandService(approvals=approval_service).handle(first.session_id, "LISTAR APPROVALS PENDENTES")

    assert response is not None
    assert response.status == "ok"
    assert first.approval_id in response.message
    assert f"APROVAR {first.approval_id}" in response.message
    assert response.contract_preview["approvals"]


def test_list_approvals_no_pending_returns_none(tmp_path: Path) -> None:
    approval_service = ApprovalService(store=ApprovalStore(tmp_path / "empty_approvals"))

    response = ChatApprovalCommandService(approvals=approval_service).handle("chat_empty", "LISTAR APROVACOES PENDENTES")

    assert response is not None
    assert response.status == "ok"
    assert "NENHUM_APPROVAL_PENDENTE" in response.message
