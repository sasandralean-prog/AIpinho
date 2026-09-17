from __future__ import annotations

from pathlib import Path

from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.governance.lifecycle import CanonicalPermission
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.task_run_guard import TaskRunGuard
from aipinho.services.runtime.task_run_store import TaskRunStore
from tests.support.runtime_fixtures import runtime_run
from tests.unit.test_dynamic_local_resource_runtime import (
    _contract as local_contract,
    _dynamic_gateway,
    _resource,
)
from tests.unit.test_explicit_mission_authority import _contract as authority_contract


def _guard_run(target: Path, contract, *, action: str = "write_files"):
    run = runtime_run(
        action=action,
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        runtime_profile="write_file",
        workspace=str(target),
        policy={
            "status": "needs_approval",
            "allowed_actions": [action],
            "denied_actions": [],
            "approval_required_for": [action],
        },
    )
    run.mission_contract = contract
    run.mission_binding = contract.binding()
    return run


def _gateway_task_run(target: Path, contract, *, run_id: str) -> TaskRun:
    return TaskRun(
        run_id=run_id,
        source_type="test",
        workspace=str(target),
        contract_type="filesystem_write",
        plan=TaskRunPlan(
            plan_id=f"plan_{run_id}",
            contract_type="filesystem_write",
            steps=[],
        ),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )


def test_guard_and_gateway_agree_on_explicit_authority(tmp_path: Path) -> None:
    target, contract = authority_contract(tmp_path, authorized=True)
    existing = target / "existing.txt"
    existing.write_text("old", encoding="utf-8")
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")

    guard_decision = TaskRunGuard(authority_grants=grants).check_run(
        _guard_run(target, contract)
    )
    canonical_guard = next(
        item
        for item in guard_decision.canonical_policy_decisions
        if item.capability == "modify_file"
    )

    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = _gateway_task_run(target, contract, run_id="task_run_b5b5b5b5")
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)
    gateway.authority_grants = grants
    gateway_result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "modify_file",
        ToolInvocationCreateRequest(
            path_ref=str(existing),
            input={"content": "new"},
        ),
        task_run_id=task_run.run_id,
    )

    assert guard_decision.allowed is True
    assert canonical_guard.permission == CanonicalPermission.ALLOWED
    assert gateway_result.status == "succeeded"
    assert gateway_result.canonical_policy_decision is not None
    assert gateway_result.canonical_policy_decision.permission == CanonicalPermission.ALLOWED
    assert gateway_result.canonical_policy_decision.capability == canonical_guard.capability
    gateway_facets = {(item.facet, item.permission, item.source) for item in gateway_result.canonical_policy_decision.facets}
    assert ("resource_permission", CanonicalPermission.ASK, "workspace_permission_matrix") in gateway_facets
    assert ("human_authority", CanonicalPermission.ALLOWED, "mission_authority_grant") in gateway_facets
    assert {
        (facet.facet, facet.permission)
        for facet in canonical_guard.facets
    } >= {
        ("resource_permission", CanonicalPermission.ASK),
        ("human_authority", CanonicalPermission.ALLOWED),
    }


def test_guard_and_gateway_agree_on_readonly_resource_denial(tmp_path: Path) -> None:
    source = tmp_path / "readonly_source"
    source.mkdir()
    contract = local_contract(
        source,
        [_resource(source, "source_readonly", ["read_file", "list_files"])],
    )

    guard_decision = TaskRunGuard().check_run(_guard_run(source, contract))
    canonical_guard = next(
        item
        for item in guard_decision.canonical_policy_decisions
        if item.capability == "modify_file"
    )

    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = _gateway_task_run(source, contract, run_id="task_run_c5c5c5c5")
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)
    gateway_result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "modify_file",
        ToolInvocationCreateRequest(
            path_ref=str(source / "blocked.txt"),
            input={"content": "no"},
        ),
        task_run_id=task_run.run_id,
    )

    assert guard_decision.allowed is False
    assert canonical_guard.permission == CanonicalPermission.DENIED
    assert gateway_result.status == "blocked"
    assert gateway_result.canonical_policy_decision is not None
    assert gateway_result.canonical_policy_decision.permission == CanonicalPermission.DENIED
    assert gateway_result.canonical_policy_decision.capability == canonical_guard.capability
    blocking = next(item for item in gateway_result.canonical_policy_decision.facets if item.permission == CanonicalPermission.DENIED)
    assert blocking.facet in {"workspace_resolution", "resource_permission"}
    assert blocking.source in {"agent_tool_workspace_resolver", "workspace_permission_matrix"}
    assert not (source / "blocked.txt").exists()


def test_guard_and_gateway_agree_on_missing_human_authority(tmp_path: Path) -> None:
    target, contract = authority_contract(tmp_path, authorized=False)
    existing = target / "existing.txt"
    existing.write_text("old", encoding="utf-8")

    guard_decision = TaskRunGuard().check_run(_guard_run(target, contract))
    canonical_guard = next(
        item
        for item in guard_decision.canonical_policy_decisions
        if item.capability == "modify_file"
    )

    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = _gateway_task_run(target, contract, run_id="task_run_d5d5d5d5")
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)
    gateway_result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "modify_file",
        ToolInvocationCreateRequest(
            path_ref=str(existing),
            input={"content": "new"},
        ),
        task_run_id=task_run.run_id,
    )

    assert guard_decision.allowed is False
    assert canonical_guard.permission == CanonicalPermission.ASK
    assert gateway_result.canonical_policy_decision is not None
    assert gateway_result.canonical_policy_decision.permission == CanonicalPermission.ASK
    assert gateway_result.canonical_policy_decision.capability == canonical_guard.capability
    pending = [item for item in gateway_result.canonical_policy_decision.facets if item.permission == CanonicalPermission.ASK]
    assert any(item.facet == "resource_permission" and item.requires_human_authority for item in pending)
    assert not any(item.facet == "human_authority" and item.permission == CanonicalPermission.ALLOWED for item in gateway_result.canonical_policy_decision.facets)
    assert gateway_result.status in {"blocked", "approval_required"}
    assert existing.read_text(encoding="utf-8") == "old"


def _shell_guard_run(target: Path, contract, shell_category: str):
    run = runtime_run(
        action="run_command",
        contract_type="shell",
        operation_type="shell_execute",
        runtime_profile="shell",
        workspace=str(target),
        policy={
            "status": "needs_approval",
            "allowed_actions": ["run_command"],
            "denied_actions": [],
            "approval_required_for": ["run_command"],
        },
    )
    run.intent_map = {
        "intent_type": "shell_execute",
        "shell_plan": {"shell_category": shell_category},
    }
    run.mission_contract = contract
    run.mission_binding = contract.binding()
    return run


def test_guard_and_gateway_deny_ambiguous_external_shells(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    contract = local_contract(
        target,
        [_resource(target, "target_mutable", ["read_file", "script_execution"])],
    )
    expected = {
        "git_write_shell": "git_write_requires_granular_classification",
        "network_shell": "network_shell_requires_granular_classification",
    }

    for index, (category, reason_code) in enumerate(expected.items(), start=1):
        guard = TaskRunGuard().check_run(
            _shell_guard_run(target, contract, category)
        )
        canonical_guard = next(
            item
            for item in guard.canonical_policy_decisions
            if item.capability == "script_execution"
        )
        assert canonical_guard.permission == CanonicalPermission.DENIED
        assert reason_code in {item.reason_code for item in canonical_guard.facets}

        task_store = TaskRunStore(root=tmp_path / f"task_runs_{index}")
        task_run = _gateway_task_run(
            target,
            contract,
            run_id=f"task_run_e5e5e5e{index}",
        )
        task_store.create_run(task_run)
        gateway, agent_run = _dynamic_gateway(tmp_path / f"gateway_{index}", task_store)
        result = gateway.invoke(
            "aipinho",
            agent_run.run_id,
            "run_shell",
            ToolInvocationCreateRequest(
                path_ref=str(target),
                input={
                    "argv": ["echo", category],
                    "cwd": str(target),
                    "shell_category": category,
                },
            ),
            task_run_id=task_run.run_id,
        )
        assert result.status == "blocked"
        assert result.canonical_policy_decision is not None
        assert result.canonical_policy_decision.permission == CanonicalPermission.DENIED
