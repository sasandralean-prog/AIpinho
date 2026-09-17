from __future__ import annotations

import subprocess
from pathlib import Path

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

REPO = "https://code.example.test/team/controlled-app.git"


def _git(cwd: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=str(cwd) if cwd else None, check=True,
        text=True, capture_output=True, encoding="utf-8", errors="replace",
    )


def _configure_identity(repo: Path) -> None:
    _git(repo, "config", "user.email", "m6@example.test")
    _git(repo, "config", "user.name", "M6 Fixture")


def _repositories(tmp_path: Path) -> tuple[Path, Path]:
    bare = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    workspace = tmp_path / "workspace"
    _git(None, "init", "--bare", str(bare))
    _git(None, "init", str(seed))
    _configure_identity(seed)
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "seed")
    _git(seed, "branch", "-M", "main")
    _git(seed, "remote", "add", "origin", str(bare))
    _git(seed, "push", "-u", "origin", "main")
    _git(None, f"--git-dir={bare}", "symbolic-ref", "HEAD", "refs/heads/main")
    _git(None, "clone", str(bare), str(workspace))
    _configure_identity(workspace)
    _git(workspace, "remote", "set-url", "origin", REPO)
    return workspace, bare


class LocalMappedGitRunner:
    def __init__(self, bare: Path) -> None:
        self.bare = bare
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        original = [str(item) for item in argv]
        self.calls.append(original)
        mapped = list(original)
        if len(original) >= 3 and original[:2] in (["git", "fetch"], ["git", "push"]):
            mapped = [*original]
            if mapped[2] == "origin":
                mapped[2] = str(self.bare)
        elif len(original) >= 3 and original[:2] == ["git", "ls-remote"]:
            mapped = ["git", "ls-remote", str(self.bare), *original[3:]]
        return subprocess.run(
            mapped,
            cwd=kwargs.get("cwd"),
            timeout=kwargs.get("timeout"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )


def _contract(target: Path, capability: str, phrase: str):
    prompt = (
        f"Use repository {REPO} branch main and {phrase}. "
        f"AUTORIZACAO: Autorizo {phrase} nesta missao."
    )
    human = IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=[capability],
    )
    remote = IntentRemoteRepositoryService().resolve(prompt).resources
    local = MissionResourceScope(
        resource_id="resource_controlled_git",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(target),
        permissions=["script_execution"],
        provenance_refs=["m6_controlled_fixture"],
    )
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id=f"session_{capability}",
        source_message_id=f"msg_{capability}",
        workspace=str(target),
        contract_type="shell",
        operation_type=capability,
        runtime_profile="shell",
        capabilities_required=[capability],
        requested_actions=["run_command"],
        intent_map={
            "intent_type": "run_command",
            "raw_prompt": prompt,
            "requested_capabilities": [capability],
            "authorized_capabilities": human.authorized_capabilities,
            "authority_evidence": human.evidence,
            "local_resources": [local.model_dump(mode="json")],
            "remote_resources": [item.model_dump(mode="json") for item in remote],
        },
    )
    return MissionContractService().compile_from_request(request)


def _service(tmp_path: Path, workspace: Path, bare: Path, capability: str, phrase: str):
    contract = _contract(workspace, capability, phrase)
    store = TaskRunStore(root=tmp_path / f"task_runs_{capability}")
    suffix = {"git_fetch": "fa12ab34", "git_commit": "ca12ab34", "git_push": "da12ab34"}[capability]
    run = TaskRun(
        run_id=f"task_run_{suffix}",
        source_type="test",
        workspace=str(workspace),
        contract_type="shell",
        plan=TaskRunPlan(
            plan_id=f"plan_{capability}",
            contract_type="shell",
            steps=[],
        ),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    store.create_run(run)
    grants = AuthorityGrantService(store_dir=tmp_path / f"grants_{capability}")
    runner = LocalMappedGitRunner(bare)
    service = GovernedToolExecutionService(
        runner=runner,
        task_runs=store,
        authority_grants=grants,
    )
    return service, run, runner


def _request(workspace: Path, run: TaskRun, argv: list[str]):
    return ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        task_run_id=run.run_id,
        input={
            "workspace": str(workspace),
            "argv": argv,
            "repository_locator": REPO,
            "branch": "main",
        },
    )


def _remote_head(bare: Path) -> str:
    return _git(None, f"--git-dir={bare}", "rev-parse", "refs/heads/main").stdout.strip()


def test_controlled_fixture_allows_real_git_fetch(tmp_path: Path) -> None:
    workspace, bare = _repositories(tmp_path)
    updater = tmp_path / "updater"
    _git(None, "clone", str(bare), str(updater))
    _configure_identity(updater)
    (updater / "README.md").write_text("seed\nremote update\n", encoding="utf-8")
    _git(updater, "add", "README.md")
    _git(updater, "commit", "-m", "remote update")
    _git(updater, "push", "origin", "main")
    before = _git(workspace, "rev-parse", "refs/remotes/origin/main").stdout.strip()

    service, run, _runner = _service(tmp_path, workspace, bare, "git_fetch", "git fetch")
    result = service.execute(_request(workspace, run, ["git", "fetch", "origin", "main"]))
    fetched = _git(workspace, "rev-parse", "FETCH_HEAD").stdout.strip()

    assert result.status == "executed_governed"
    assert fetched != before
    assert fetched == _remote_head(bare)


def test_controlled_fixture_allows_real_git_commit(tmp_path: Path) -> None:
    workspace, bare = _repositories(tmp_path)
    (workspace / "README.md").write_text("seed\nlocal commit\n", encoding="utf-8")
    _git(workspace, "add", "README.md")
    service, run, _runner = _service(tmp_path, workspace, bare, "git_commit", "git commit")

    result = service.execute(
        _request(workspace, run, ["git", "commit", "-m", "governed commit"])
    )

    assert result.status == "executed_governed"
    assert _git(workspace, "log", "-1", "--pretty=%s").stdout.strip() == "governed commit"


def test_controlled_fixture_allows_real_git_push_and_refreshes_remote_head(tmp_path: Path) -> None:
    workspace, bare = _repositories(tmp_path)
    (workspace / "README.md").write_text("seed\npush commit\n", encoding="utf-8")
    _git(workspace, "add", "README.md")
    _git(workspace, "commit", "-m", "push commit")
    local_head = _git(workspace, "rev-parse", "HEAD").stdout.strip()
    service, run, _runner = _service(tmp_path, workspace, bare, "git_push", "git push")

    result = service.execute(_request(workspace, run, ["git", "push", "origin", "main"]))

    assert result.status == "executed_governed"
    assert result.safe_to_execute is True
    assert _remote_head(bare) == local_head
    assert result.metadata["local_head"] == result.metadata["remote_head"] == local_head


def test_controlled_fixture_denies_wrong_observed_remote(tmp_path: Path) -> None:
    workspace, bare = _repositories(tmp_path)
    _git(workspace, "remote", "set-url", "origin", "https://code.example.test/team/other.git")
    service, run, runner = _service(tmp_path, workspace, bare, "git_push", "git push")
    before = _remote_head(bare)

    result = service.execute(_request(workspace, run, ["git", "push", "origin", "main"]))

    assert result.status == "blocked"
    assert "remote_identity_changed_before_execution" in result.violations
    assert _remote_head(bare) == before
    assert ["git", "push", "origin", "main"] not in runner.calls


def test_controlled_fixture_denies_wrong_current_branch(tmp_path: Path) -> None:
    workspace, bare = _repositories(tmp_path)
    _git(workspace, "checkout", "-b", "other")
    service, run, runner = _service(tmp_path, workspace, bare, "git_push", "git push")
    before = _remote_head(bare)

    result = service.execute(_request(workspace, run, ["git", "push", "origin", "main"]))

    assert result.status == "blocked"
    assert "git_push_current_branch_mismatch" in result.violations
    assert _remote_head(bare) == before
    assert ["git", "push", "origin", "main"] not in runner.calls


def test_controlled_fixture_denies_destructive_force_push(tmp_path: Path) -> None:
    workspace, bare = _repositories(tmp_path)
    service, run, runner = _service(tmp_path, workspace, bare, "git_push", "git push")
    before = _remote_head(bare)

    result = service.execute(
        _request(workspace, run, ["git", "push", "--force", "origin", "main"])
    )

    assert result.status == "blocked"
    assert _remote_head(bare) == before
    assert ["git", "push", "--force", "origin", "main"] not in runner.calls
