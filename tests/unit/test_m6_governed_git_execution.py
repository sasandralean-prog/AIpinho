from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.governance.intent_human_authority_service import IntentHumanAuthorityService
from aipinho.services.governance.intent_remote_repository_service import IntentRemoteRepositoryService
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService

REPO = "https://code.example.test/team/app.git"
REPO_OTHER = "https://code.example.test/team/other.git"


class FakeGitRunner:
    def __init__(self, *, remote: str = REPO, branch: str = "main", local_head: str = "abc123", remote_head: str = "abc123") -> None:
        self.remote = remote
        self.branch = branch
        self.local_head = local_head
        self.remote_head = remote_head
        self.calls: list[list[str]] = []
    def __call__(self, argv, **kwargs):
        call = [str(item) for item in argv]
        self.calls.append(call)
        assert kwargs["shell"] is False
        if call[:3] == ["git", "remote", "get-url"]:
            return SimpleNamespace(returncode=0, stdout=f"{self.remote}\n", stderr="")
        if call[:3] == ["git", "branch", "--show-current"]:
            return SimpleNamespace(returncode=0, stdout=f"{self.branch}\n", stderr="")
        if call[:3] == ["git", "rev-parse", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout=f"{self.local_head}\n", stderr="")
        if call[:2] == ["git", "ls-remote"]:
            return SimpleNamespace(
                returncode=0,
                stdout=f"{self.remote_head}\trefs/heads/{self.branch}\n",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")


def _contract(target: Path):
    prompt = (
        f"Use repository {REPO} branch main and git push. "
        "AUTORIZACAO: Autorizo git push nesta missao."
    )
    human = IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=["git_push"],
    )
    remote = IntentRemoteRepositoryService().resolve(prompt).resources
    local = MissionResourceScope(
        resource_id="resource_git_target",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(target),
        permissions=["script_execution"],
        provenance_refs=["m6_test"],
    )
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id="session_m6",
        source_message_id="msg_m6",
        workspace=str(target),
        contract_type="shell",
        operation_type="git_push",
        runtime_profile="shell",
        capabilities_required=["git_push"],
        requested_actions=["run_command"],
        intent_map={
            "intent_type": "workspace_fix_request",
            "raw_prompt": prompt,
            "requested_capabilities": ["git_push"],
            "authorized_capabilities": human.authorized_capabilities,
            "authority_evidence": human.evidence,
            "local_resources": [local.model_dump(mode="json")],
            "remote_resources": [item.model_dump(mode="json") for item in remote],
        },
    )
    return MissionContractService().compile_from_request(request)


def _service(tmp_path: Path, runner: FakeGitRunner):
    target = tmp_path / "repo"
    target.mkdir()
    contract = _contract(target)
    store = TaskRunStore(root=tmp_path / "task_runs")
    run = TaskRun(
        run_id="task_run_b1b1b1b1",
        source_type="test",
        workspace=str(target),
        contract_type="shell",
        plan=TaskRunPlan(
            plan_id="plan_task_run_b1b1b1b1",
            contract_type="shell",
            steps=[],
        ),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    store.create_run(run)
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    service = GovernedToolExecutionService(
        runner=runner,
        task_runs=store,
        authority_grants=grants,
    )
    return service, run, grants, target


def _push_request(target: Path, run: TaskRun, argv: list[str] | None = None):
    return ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        task_run_id=run.run_id,
        input={
            "workspace": str(target),
            "argv": argv or ["git", "push", "origin", "main"],
            "repository_locator": REPO,
            "branch": "main",
        },
    )


def test_authorized_push_reobserves_scope_consumes_grant_and_validates_remote_head(tmp_path: Path) -> None:
    runner = FakeGitRunner()
    service, run, grants, target = _service(tmp_path, runner)
    request = _push_request(target, run)

    preview = service.preview_decision(request)
    result = service.execute(request)

    assert preview["canonical_policy"]["permission"] == "allowed"
    assert preview["capability"] == "git_push"
    assert result.status == "executed_governed"
    assert result.safe_to_execute is True
    assert result.metadata["local_head"] == result.metadata["remote_head"] == "abc123"
    assert ["git", "remote", "get-url", "origin"] in runner.calls
    assert ["git", "branch", "--show-current"] in runner.calls
    assert ["git", "push", "origin", "main"] in runner.calls
    assert ["git", "rev-parse", "HEAD"] in runner.calls
    assert ["git", "ls-remote", "origin", "main"] in runner.calls
    assert runner.calls.index(["git", "remote", "get-url", "origin"]) < runner.calls.index(["git", "push", "origin", "main"])
    grant = grants.ensure_mission_grant(run.mission_contract)
    assert grant is not None and grant.used_count == 1


def test_observed_wrong_remote_is_denied_before_push(tmp_path: Path) -> None:
    runner = FakeGitRunner(remote=REPO_OTHER)
    service, run, _grants, target = _service(tmp_path, runner)

    result = service.execute(_push_request(target, run))

    assert result.status == "blocked"
    assert "remote_identity_changed_before_execution" in result.violations
    assert ["git", "push", "origin", "main"] not in runner.calls


def test_observed_wrong_branch_is_denied_before_push(tmp_path: Path) -> None:
    runner = FakeGitRunner(branch="release")
    service, run, _grants, target = _service(tmp_path, runner)

    result = service.execute(_push_request(target, run))

    assert result.status == "blocked"
    assert "git_push_current_branch_mismatch" in result.violations
    assert ["git", "push", "origin", "main"] not in runner.calls


def test_force_push_remains_blocked_before_mutable_execution(tmp_path: Path) -> None:
    runner = FakeGitRunner()
    service, run, _grants, target = _service(tmp_path, runner)
    request = _push_request(target, run, ["git", "push", "--force", "origin", "main"])

    result = service.execute(request)

    assert result.status == "blocked"
    assert not any(call[:2] == ["git", "push"] for call in runner.calls)


def test_push_requires_refreshed_remote_head_match(tmp_path: Path) -> None:
    runner = FakeGitRunner(remote_head="different")
    service, run, _grants, target = _service(tmp_path, runner)

    result = service.execute(_push_request(target, run))

    assert result.status == "degraded"
    assert result.safe_to_execute is False
    assert "git_push_remote_head_mismatch" in result.violations
    assert result.metadata["local_head"] == "abc123"
    assert result.metadata["remote_head"] == "different"
