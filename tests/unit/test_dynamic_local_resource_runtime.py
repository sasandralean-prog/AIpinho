from __future__ import annotations

from pathlib import Path

import subprocess
import yaml

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.patching.patch_target_guard import PatchTargetGuard
from aipinho.services.orchestration.mission_execution_strategy_service import MissionExecutionStrategyService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.workspace_context_service import WorkspaceContextService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


def _registry(path: Path, workspaces: list[dict[str, object]] | None = None) -> Path:
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "workspaces": workspaces or []}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _resource(root: Path, role: str, permissions: list[str], *, kind: str = "project") -> MissionResourceScope:
    return MissionResourceScope(
        resource_id=f"resource_{root.name}_{role}",
        resource_type="local_workspace",
        role=role,
        locator=str(root),
        permissions=permissions,
        provenance_refs=["test_prompt_scope"],
        metadata={"kind": kind},
    )


def _contract(root: Path, resources: list[MissionResourceScope]):
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        workspace=str(root),
        contract_type="readonly_analysis",
        operation_type="project_analysis",
        runtime_profile="readonly_analysis",
        capabilities_required=["read_workspace"],
        intent_map={
            "intent_type": "workspace_fix_request",
            "raw_prompt": "generic mission prompt",
            "requested_capabilities": sorted({p for item in resources for p in item.permissions}),
            "local_resources": [item.model_dump(mode="json") for item in resources],
        },
    )
    return MissionContractService().compile_from_request(request)


def test_semantic_ingress_compiles_dynamic_target_and_readonly_corpus(tmp_path: Path) -> None:
    target = tmp_path / "DynamicApp"
    corpus = tmp_path / "ReadonlyCorpus"
    prompt = (
        f"Execute uma missão end-to-end para corrigir e validar o aplicativo.\n"
        f"WORKSPACE DO APP A SER CORRIGIDO: {target}\n"
        f"CORPUS DE TESTES — SOMENTE LEITURA: {corpus}\n"
        "Edite o código quando necessário, compile e execute os testes. Não modifique o corpus."
    )

    decision = SemanticIntentResolutionService().resolve(
        prompt,
        source_channel="unit",
        workspace_hint=str(target),
    )
    by_path = {Path(item.locator): item for item in decision.local_resources if item.locator}

    assert decision.mission_execution_mode == "end_to_end_governed"
    assert by_path[target].role == "target_mutable"
    assert {"create_directory", "create_file", "modify_file", "apply_patch", "shell_build", "shell_test"} <= set(
        by_path[target].permissions
    )
    assert by_path[corpus].role == "source_readonly"
    assert set(by_path[corpus].permissions) == {"read_file", "list_files", "copy_from"}



def test_multi_phase_repair_strategy_handles_portuguese_infinitive() -> None:
    strategy = MissionExecutionStrategyService().resolve(
        prompt="Investigar o problema, corrigir o codigo e depois executar testes e build.",
        semantic_graph={"mutation_intent": True, "execution_intent": True},
    )

    assert strategy == "end_to_end_governed"

def test_permission_matrix_uses_dynamic_scope_but_requires_declared_permission(tmp_path: Path) -> None:
    registry = _registry(tmp_path / "registry.yaml")
    matrix = WorkspacePermissionMatrixService(registry).load()
    target = tmp_path / "target"
    target.mkdir()
    scope = _resource(
        target,
        "target_mutable",
        ["read_file", "list_files", "create_directory", "modify_file"],
    )

    read = matrix.decide_with_resources(
        path=str(target / "file.txt"),
        permission="read_file",
        local_resources=[scope],
    )
    write = matrix.decide_with_resources(
        path=str(target / "file.txt"),
        permission="modify_file",
        local_resources=[scope],
    )
    missing = matrix.decide_with_resources(
        path=str(target / "file.txt"),
        permission="apply_patch",
        local_resources=[scope],
    )

    assert read.status == "allowed"
    assert write.status == "approval_required"
    assert missing.status == "denied"
    assert missing.reason_code == "permission_not_declared_by_mission_resource"


def test_static_readonly_child_overrides_dynamic_mutable_parent(tmp_path: Path) -> None:
    target = tmp_path / "target"
    readonly_child = target / "readonly"
    readonly_child.mkdir(parents=True)
    registry = _registry(
        tmp_path / "registry.yaml",
        [{"workspace_id": "readonly_child", "root_path": str(readonly_child), "role": "source_readonly"}],
    )
    matrix = WorkspacePermissionMatrixService(registry).load()
    roles = WorkspaceRoleContractService(registry).load()
    scope = _resource(target, "target_mutable", ["read_file", "modify_file", "apply_patch"])

    role_decision = roles.resolve_with_resources(
        str(readonly_child / "file.py"),
        local_resources=[scope],
    )
    permission = matrix.decide_with_resources(
        path=str(readonly_child / "file.py"),
        permission="modify_file",
        local_resources=[scope],
    )

    assert role_decision.contract is not None
    assert role_decision.contract.role == "source_readonly"
    assert permission.status == "denied"


def test_workspace_context_rehydrates_resources_from_mission_contract(tmp_path: Path) -> None:
    target = tmp_path / "target"
    corpus = tmp_path / "corpus"
    target.mkdir()
    corpus.mkdir()
    resources = [
        _resource(target, "target_mutable", ["read_file", "modify_file"]),
        _resource(corpus, "source_readonly", ["read_file", "list_files"], kind="library"),
    ]
    contract = _contract(target, resources)
    run = TaskRun(
        run_id="task_run_dynamic_context",
        source_type="test",
        workspace=str(target),
        contract_type="readonly_analysis",
        plan=TaskRunPlan(plan_id="plan_dynamic_context", contract_type="readonly_analysis", steps=[]),
        mission_contract=contract,
        mission_binding=contract.binding(),
    )

    context = WorkspaceContextService().from_run(run)

    assert set(context.workspace_ids) >= {item.resource_id for item in resources}
    assert str(target.resolve()) in context.allowed_roots
    assert str(corpus.resolve()) in context.library_roots
    assert context.readonly_flags[str(target.resolve())] is False
    assert context.readonly_flags[str(corpus.resolve())] is True
    assert {item.resource_id for item in context.local_resources} == {
        item.resource_id for item in resources
    }


def test_patch_guard_accepts_dynamic_target_and_rejects_readonly_scope(tmp_path: Path) -> None:
    registry = _registry(tmp_path / "registry.yaml")
    roles = WorkspaceRoleContractService(registry).load()
    matrix = WorkspacePermissionMatrixService(registry).load()
    target = tmp_path / "target"
    readonly = tmp_path / "readonly"
    target.mkdir()
    readonly.mkdir()
    target_file = target / "main.py"
    readonly_file = readonly / "main.py"
    target_file.write_text("print('old')\n", encoding="utf-8")
    readonly_file.write_text("print('old')\n", encoding="utf-8")
    guard = PatchTargetGuard(roles=roles, permissions=matrix)

    mutable_result = guard.validate(
        str(target),
        str(target_file),
        local_resources=[_resource(target, "target_mutable", ["read_file", "apply_patch"])],
    )
    readonly_result = guard.validate(
        str(readonly),
        str(readonly_file),
        local_resources=[_resource(readonly, "source_readonly", ["read_file"])],
    )

    assert mutable_result.status == "allowed"
    assert readonly_result.status == "blocked"
    assert "permission_not_declared_by_mission_resource" in readonly_result.blocked_reasons


class _FakeShellRunner:
    def run(self, argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


def _dynamic_gateway(tmp_path: Path, task_store: TaskRunStore):
    config_root = tmp_path / "agent_config"
    agents = config_root / "agents"
    agents.mkdir(parents=True)
    for name in ("tool_gateway_registry.yaml", "tool_gateway_policy.yaml"):
        (agents / name).write_text(
            Path(f"config/agents/{name}").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (agents / "tool_gateway_workspaces.yaml").write_text(
        "version: 1\nworkspaces: []\n",
        encoding="utf-8",
    )
    permission_registry = _registry(tmp_path / "permission_registry.yaml")
    matrix = WorkspacePermissionMatrixService(permission_registry).load()
    kernel = AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        registry=AgentToolRegistryService(agents / "tool_gateway_registry.yaml", root=config_root),
        resolver=AgentToolWorkspaceResolver(agents / "tool_gateway_workspaces.yaml", root=config_root),
        policy=AgentToolPolicyDecisionService(agents / "tool_gateway_policy.yaml", root=config_root),
        store=AgentToolInvocationStore(tmp_path / "tool_gateway"),
        task_runs=task_store,
        permission_matrix=matrix,
        shell_runner=_FakeShellRunner(),
    )
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="dynamic"))
    agent_run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="tool_test", status="running"),
    )
    return gateway, agent_run


def test_tool_gateway_enforces_dynamic_permission_at_final_gate(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    existing = target / "existing.txt"
    existing.write_text("hello", encoding="utf-8")
    resources = [_resource(target, "target_mutable", ["read_file", "create_directory"])]
    contract = _contract(target, resources)
    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = TaskRun(
        run_id="task_run_abc123",
        source_type="test",
        workspace=str(target),
        contract_type="filesystem_write",
        plan=TaskRunPlan(plan_id="plan_dynamic_gateway", contract_type="filesystem_write", steps=[]),
        status="running",
        approval_id="approval_dynamic",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)

    read = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "read_file",
        ToolInvocationCreateRequest(path_ref=str(existing)),
        task_run_id=task_run.run_id,
    )
    undeclared = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "create_file",
        ToolInvocationCreateRequest(path_ref=str(target / "blocked.txt"), input={"content": "no"}),
        task_run_id=task_run.run_id,
    )

    assert read.status == "succeeded"
    assert undeclared.status == "blocked"
    assert undeclared.workspace_resolution is not None
    assert undeclared.workspace_resolution.reason_code == "permission_not_declared_by_mission_resource"
    assert not (target / "blocked.txt").exists()


def test_dynamic_mutation_requires_canonical_task_approval_binding(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    resources = [_resource(target, "target_mutable", ["read_file", "create_directory"])]
    contract = _contract(target, resources)
    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = TaskRun(
        run_id="task_run_def456",
        source_type="test",
        workspace=str(target),
        contract_type="filesystem_write",
        plan=TaskRunPlan(plan_id="plan_dynamic_approval", contract_type="filesystem_write", steps=[]),
        status="running",
        approval_id="approval_dynamic",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)

    blocked = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "create_directory",
        ToolInvocationCreateRequest(path_ref=str(target / "blocked_dir")),
        task_run_id=task_run.run_id,
    )
    approved = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "create_directory",
        ToolInvocationCreateRequest(
            path_ref=str(target / "approved_dir"),
            approval_id="approval_dynamic",
        ),
        task_run_id=task_run.run_id,
    )

    assert blocked.status == "blocked"
    assert blocked.workspace_resolution is not None
    assert blocked.workspace_resolution.reason_code == "mission_resource_requires_canonical_task_approval"
    assert approved.status == "succeeded"
    assert (target / "approved_dir").is_dir()


def test_directory_creation_requires_explicit_creation_language() -> None:
    from aipinho.services.agents.agent_local_action_planner import AgentLocalActionPlanner

    planner = AgentLocalActionPlanner()

    assert planner.extract_requested_directory(
        "Crie uma pasta chamada output/reports dentro do workspace."
    ) == "output/reports"
    assert planner.extract_requested_directory(
        "O workspace local corresponde ao subdiretório AppDesktop/ do repositório."
    ) is None


def test_unregistered_dynamic_target_supports_full_local_governed_surface(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    readonly = tmp_path / "readonly_source"
    target.mkdir()
    readonly.mkdir()
    source_file = readonly / "source.txt"
    source_file.write_text("source", encoding="utf-8")
    permissions = [
        "read_file", "list_files", "create_directory", "create_file", "modify_file",
        "apply_patch", "shell_readonly", "shell_build", "shell_test", "script_execution",
    ]
    resources = [
        _resource(target, "target_mutable", permissions),
        _resource(readonly, "source_readonly", ["read_file", "list_files", "copy_from"]),
    ]
    contract = _contract(target, resources)
    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = TaskRun(
        run_id="task_run_a1b2c3d4",
        source_type="test",
        workspace=str(target),
        contract_type="filesystem_write",
        plan=TaskRunPlan(plan_id="plan_full_dynamic_surface", contract_type="filesystem_write", steps=[]),
        status="running",
        approval_id="approval_dynamic",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)

    def invoke(tool_name: str, *, path: Path, input: dict | None = None):
        return gateway.invoke(
            "aipinho", agent_run.run_id, tool_name,
            ToolInvocationCreateRequest(
                path_ref=str(path),
                approval_id="approval_dynamic",
                input=input or {},
            ),
            task_run_id=task_run.run_id,
        )

    created_dir = invoke("create_directory", path=target / "generated")
    created_file = invoke("create_file", path=target / "generated" / "main.txt", input={"content": "one"})
    modified_file = invoke("modify_file", path=target / "generated" / "main.txt", input={"content": "two"})
    patch_contract = invoke("patch_apply", path=target / "generated" / "main.txt", input={"files_changed": ["generated/main.txt"]})
    build = invoke("run_shell", path=target, input={"argv": ["gradle", "build"], "cwd": str(target), "shell_category": "build_shell"})
    test = invoke("run_shell", path=target, input={"argv": ["pytest", "-q"], "cwd": str(target), "shell_category": "test_shell"})
    readonly_write = invoke("create_file", path=readonly / "blocked.txt", input={"content": "no"})

    assert [created_dir.status, created_file.status, modified_file.status, patch_contract.status, build.status, test.status] == ["succeeded"] * 6
    assert (target / "generated" / "main.txt").read_text(encoding="utf-8") == "two"
    assert readonly_write.status == "blocked"
    assert not (readonly / "blocked.txt").exists()
