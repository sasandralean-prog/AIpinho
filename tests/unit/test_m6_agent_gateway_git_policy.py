from __future__ import annotations

import subprocess
from pathlib import Path

from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService
from tests.unit.test_dynamic_local_resource_runtime import _dynamic_gateway
from tests.unit.test_m6_governed_git_execution import REPO, REPO_OTHER, _contract


class AgentGitRunner:
    def __init__(self, *, remote: str = REPO, branch: str = "main", local_head: str = "abc123", remote_head: str = "abc123") -> None:
        self.remote = remote
        self.branch = branch
        self.local_head = local_head
        self.remote_head = remote_head
        self.calls: list[list[str]] = []

    def run(self, argv, cwd, timeout):
        call = [str(item) for item in argv]
        self.calls.append(call)
        if call[:3] == ["git", "remote", "get-url"]:
            return subprocess.CompletedProcess(call, 0, stdout=f"{self.remote}\n", stderr="")
        if call[:3] == ["git", "branch", "--show-current"]:
            return subprocess.CompletedProcess(call, 0, stdout=f"{self.branch}\n", stderr="")
        if call[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(call, 0, stdout=f"{self.local_head}\n", stderr="")
        if call[:2] == ["git", "ls-remote"]:
            return subprocess.CompletedProcess(
                call,
                0,
                stdout=f"{self.remote_head}\trefs/heads/{self.branch}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(call, 0, stdout="ok\n", stderr="")


def _gateway_fixture(tmp_path: Path, *, runner: AgentGitRunner):
    target = tmp_path / "repo"
    target.mkdir()
    contract = _contract(target)
    store = TaskRunStore(root=tmp_path / "task_runs")
    run = TaskRun(
        run_id="task_run_b2b2b2b2",
        source_type="test",
        workspace=str(target),
        contract_type="shell",
        plan=TaskRunPlan(plan_id="plan_b2b2b2b2", contract_type="shell", steps=[]),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    store.create_run(run)
    gateway, agent_run = _dynamic_gateway(tmp_path, store)
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    gateway.authority_grants = grants
    gateway.shell_runner = runner

    def bridge(argv, *, cwd=None, timeout=30, **_kwargs):
        return runner.run([str(item) for item in argv], cwd=cwd, timeout=int(timeout))

    gateway.governed_execution = GovernedToolExecutionService(
        runner=bridge,
        task_runs=store,
        authority_grants=grants,
    )
    return gateway, agent_run, run, grants, target


def _push_request(target: Path, run: TaskRun, argv: list[str] | None = None):
    resource_id = run.mission_contract.local_resources[0].resource_id
    return ToolInvocationCreateRequest(
        workspace_id=resource_id,
        input={
            "argv": argv or ["git", "push", "origin", "main"],
            "cwd": str(target),
            "shell_category": "readonly_shell",
            "repository_locator": REPO,
            "branch": "main",
        },
    )


def test_gateway_reclassifies_and_delegates_authorized_git_push(tmp_path: Path) -> None:
    runner = AgentGitRunner()
    gateway, agent_run, run, grants, target = _gateway_fixture(tmp_path, runner=runner)

    result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "run_shell",
        _push_request(target, run),
        task_run_id=run.run_id,
    )

    assert result.status == "succeeded"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.capability == "git_push"
    assert result.output["governed_status"] == "executed_governed"
    assert ["git", "remote", "get-url", "origin"] in runner.calls
    assert ["git", "branch", "--show-current"] in runner.calls
    assert ["git", "push", "origin", "main"] in runner.calls
    assert ["git", "rev-parse", "HEAD"] in runner.calls
    grant = grants.ensure_mission_grant(run.mission_contract)
    assert grant is not None and grant.used_count == 1


def test_gateway_propagates_jit_remote_mismatch_as_blocked(tmp_path: Path) -> None:
    runner = AgentGitRunner(remote=REPO_OTHER)
    gateway, agent_run, run, _grants, target = _gateway_fixture(tmp_path, runner=runner)

    result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "run_shell",
        _push_request(target, run),
        task_run_id=run.run_id,
    )

    assert result.status == "blocked"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.permission.value == "denied"
    assert "remote_identity_changed_before_execution" in result.output["violations"]
    assert ["git", "push", "origin", "main"] not in runner.calls


def test_gateway_blocks_force_push_before_delegated_execution(tmp_path: Path) -> None:
    runner = AgentGitRunner()
    gateway, agent_run, run, _grants, target = _gateway_fixture(tmp_path, runner=runner)
    request = _push_request(target, run, ["git", "push", "--force", "origin", "main"])

    result = gateway.invoke(
        "aipinho", agent_run.run_id, "run_shell", request, task_run_id=run.run_id
    )

    assert result.status == "blocked"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.capability == "git_destructive"
    assert not any(call[:2] == ["git", "push"] for call in runner.calls)
