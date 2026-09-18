from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.governance.intent_human_authority_service import IntentHumanAuthorityService
from aipinho.services.governance.intent_remote_repository_service import IntentRemoteRepositoryService
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.mission_staging_materialization_service import MissionStagingMaterializationService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService

REPO = "https://code.example.test/team/staging-app.git"


def _git(cwd: Path | None, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
def _bare_repository(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    _git(None, "init", "--bare", str(bare))
    _git(None, "init", str(seed))
    _git(seed, "config", "user.email", "m7@example.test")
    _git(seed, "config", "user.name", "M7 Fixture")
    (seed / "README.md").write_text("seed\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "seed")
    _git(seed, "branch", "-M", "main")
    _git(seed, "remote", "add", "origin", str(bare))
    _git(seed, "push", "-u", "origin", "main")
    _git(None, f"--git-dir={bare}", "symbolic-ref", "HEAD", "refs/heads/main")
    return bare


class RewriteCloneRunner:
    def __init__(self, bare: Path) -> None:
        self.bare = bare
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        original = [str(item) for item in argv]
        self.calls.append(original)
        mapped = list(original)
        if len(original) >= 2 and original[0].lower().endswith("git") and original[1] == "clone":
            mapped = [
                "git",
                "-c",
                f"url.{self.bare.as_uri()}.insteadOf={REPO}",
                *original[1:],
            ]
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


def _contract(*, authorize_clone: bool = True):
    token = uuid4().hex
    prompt = (
        f"Use repository {REPO} branch main and git clone. "
        + ("AUTORIZACAO: Autorizo git clone nesta missao." if authorize_clone else "")
    )
    human = IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=["git_clone"],
    )
    remote = IntentRemoteRepositoryService().resolve(prompt).resources
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id=f"session_m7_materialization_{token}",
        source_message_id=f"msg_m7_materialization_{token}",
        contract_type="shell",
        operation_type="git_clone",
        runtime_profile="shell",
        capabilities_required=["git_clone"],
        requested_actions=["run_command"],
        intent_map={
            "intent_type": "git_clone",
            "raw_prompt": prompt,
            "requested_capabilities": ["git_clone"],
            "authorized_capabilities": human.authorized_capabilities,
            "authority_evidence": human.evidence,
            "remote_resources": [item.model_dump(mode="json") for item in remote],
        },
    )
    return MissionContractService().compile_from_request(request)


def _parent(store: TaskRunStore, contract) -> TaskRun:
    run = TaskRun(
        run_id="task_run_b7a10001",
        source_type="test",
        session_id=contract.session_id,
        mission_contract=contract,
        mission_binding=contract.binding(),
        contract_type="shell",
        operation_type="git_clone",
        runtime_profile="shell",
        capabilities_required=["git_clone"],
        requested_actions=["run_command"],
        status="running",
        plan=TaskRunPlan(plan_id="plan_m7_parent", contract_type="shell", steps=[]),
    )
    store.create_run(run)
    return run


def _service(tmp_path: Path, bare: Path, store: TaskRunStore):
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    runner = RewriteCloneRunner(bare)
    runtime = TaskRuntimeService(store=store)
    tools = GovernedToolExecutionService(
        task_runs=store,
        authority_grants=grants,
        runner=runner,
    )
    service = MissionStagingMaterializationService(
        task_runs=store,
        runtime=runtime,
        tools=tools,
        authority_grants=grants,
    )
    return service, runner
def test_materializes_real_clone_in_derived_staging(tmp_path: Path) -> None:
    bare = _bare_repository(tmp_path)
    store = TaskRunStore(root=tmp_path / "task_runs")
    contract = _contract()
    parent = _parent(store, contract)
    remote = contract.remote_resources[0]
    service, runner = _service(tmp_path, bare, store)

    result = service.materialize(
        parent_run_id=parent.run_id,
        remote_resource_id=remote.resource_id,
        branch="main",
    )
    staging = Path(result.workspace_path or "")
    try:
        assert result.status == "materialized", (result.reason_code, result.violations, runner.calls)
        assert result.child_task_run_id
        assert staging.is_dir()
        assert (staging / ".git").is_dir()
        assert _git(staging, "remote", "get-url", "origin").stdout.strip() == REPO
        assert _git(staging, "branch", "--show-current").stdout.strip() == "main"
        child = store.get_run(result.child_task_run_id)
        assert child is not None and child.mission_contract is not None
        assert any(item.resource_type == "mission_staging" for item in child.mission_contract.local_resources)
        assert ["git", "clone", "--branch", "main", REPO, "."] in runner.calls
    finally:
        if staging:
            shutil.rmtree(staging.parent, ignore_errors=True)


def test_wrong_branch_blocks_before_directory_materialization(tmp_path: Path) -> None:
    bare = _bare_repository(tmp_path)
    store = TaskRunStore(root=tmp_path / "task_runs")
    contract = _contract()
    parent = _parent(store, contract)
    remote = contract.remote_resources[0]
    service, runner = _service(tmp_path, bare, store)

    result = service.materialize(
        parent_run_id=parent.run_id,
        remote_resource_id=remote.resource_id,
        branch="release",
    )

    assert result.status == "blocked"
    assert result.reason_code == "mission_staging_branch_not_authorized"
    assert runner.calls == []


def test_missing_clone_authority_blocks_before_materialization(tmp_path: Path) -> None:
    bare = _bare_repository(tmp_path)
    store = TaskRunStore(root=tmp_path / "task_runs")
    contract = _contract(authorize_clone=False)
    parent = _parent(store, contract)
    remote = contract.remote_resources[0]
    service, runner = _service(tmp_path, bare, store)

    result = service.materialize(
        parent_run_id=parent.run_id,
        remote_resource_id=remote.resource_id,
        branch="main",
    )

    assert result.status == "blocked"
    assert result.reason_code in {
        "mission_staging_source_remote_not_human_authorized",
        "mission_staging_clone_not_human_authorized",
    }
    assert runner.calls == []
