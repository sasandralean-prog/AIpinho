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
from aipinho.services.runtime.workspace_context_service import WorkspaceContextService
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


def _advance_bare(tmp_path: Path, bare: Path) -> str:
    updater = tmp_path / f"updater_{uuid4().hex}"
    _git(None, "clone", str(bare), str(updater))
    _git(updater, "config", "user.email", "m7@example.test")
    _git(updater, "config", "user.name", "M7 Fixture")
    readme = updater / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "remote update\n", encoding="utf-8")
    _git(updater, "add", "README.md")
    _git(updater, "commit", "-m", "remote update")
    _git(updater, "push", "origin", "main")
    return _git(None, f"--git-dir={bare}", "rev-parse", "refs/heads/main").stdout.strip()


class RewriteCloneRunner:
    def __init__(self, bare: Path) -> None:
        self.bare = bare
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        original = [str(item) for item in argv]
        self.calls.append(original)
        mapped = list(original)
        if (
            len(original) >= 2
            and original[0].lower().endswith("git")
            and original[1] in {"clone", "fetch", "pull", "ls-remote"}
        ):
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


def _contract(*, authorize_clone: bool = True, authorize_sync: bool = False):
    token = uuid4().hex
    prompt = f"Use repository {REPO} branch main and git clone. "
    if authorize_clone:
        prompt += "AUTORIZACAO: Autorizo git clone nesta missao. "
    if authorize_sync:
        prompt += (
            "AUTORIZACAO: Autorizo git fetch nesta missao. "
            "AUTORIZACAO: Autorizo git pull --ff-only nesta missao."
        )
    prompt = prompt.strip()
    human = IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=["git_clone", "git_fetch", "git_pull_ff"],
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
        capabilities_required=["git_clone", *(["git_fetch", "git_pull_ff"] if authorize_sync else [])],
        requested_actions=["run_command"],
        intent_map={
            "intent_type": "git_clone",
            "raw_prompt": prompt,
            "requested_capabilities": ["git_clone", *(["git_fetch", "git_pull_ff"] if authorize_sync else [])],
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
        context = WorkspaceContextService().from_run(child)
        resolved_staging = str(staging.resolve(strict=False))
        assert resolved_staging in context.allowed_roots
        assert result.resource_id in context.workspace_ids
        assert context.readonly_flags[resolved_staging] is False
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


def test_synchronize_fast_forwards_real_staging_to_remote_head(tmp_path: Path) -> None:
    bare = _bare_repository(tmp_path)
    store = TaskRunStore(root=tmp_path / "task_runs_sync")
    contract = _contract(authorize_sync=True)
    parent = _parent(store, contract)
    remote = contract.remote_resources[0]
    service, runner = _service(tmp_path, bare, store)

    materialized = service.materialize(
        parent_run_id=parent.run_id,
        remote_resource_id=remote.resource_id,
        branch="main",
    )
    assert materialized.status == "materialized", materialized.model_dump(mode="json")
    assert materialized.child_task_run_id
    staging = Path(materialized.workspace_path or "")
    try:
        before = _git(staging, "rev-parse", "HEAD").stdout.strip()
        remote_head = _advance_bare(tmp_path, bare)
        assert remote_head != before

        synchronized = service.synchronize(
            child_run_id=materialized.child_task_run_id,
            remote_resource_id=remote.resource_id,
            branch="main",
        )
        assert synchronized.status == "synchronized", synchronized.model_dump(mode="json")
        assert _git(staging, "rev-parse", "HEAD").stdout.strip() == remote_head
        assert "remote update" in (staging / "README.md").read_text(encoding="utf-8")
        assert ["git", "fetch", "origin", "main"] in runner.calls
        assert ["git", "pull", "--ff-only", "origin", "main"] in runner.calls
        assert synchronized.fetch_execution_id
        assert synchronized.fast_forward_execution_id
    finally:
        shutil.rmtree(staging.parent, ignore_errors=True)


def test_synchronize_rejects_current_branch_drift_before_pull(tmp_path: Path) -> None:
    bare = _bare_repository(tmp_path)
    store = TaskRunStore(root=tmp_path / "task_runs_branch_drift")
    contract = _contract(authorize_sync=True)
    parent = _parent(store, contract)
    remote = contract.remote_resources[0]
    service, runner = _service(tmp_path, bare, store)

    materialized = service.materialize(
        parent_run_id=parent.run_id,
        remote_resource_id=remote.resource_id,
        branch="main",
    )
    assert materialized.status == "materialized"
    assert materialized.child_task_run_id
    staging = Path(materialized.workspace_path or "")
    try:
        _git(staging, "switch", "-c", "release")
        before_calls = len(runner.calls)
        synchronized = service.synchronize(
            child_run_id=materialized.child_task_run_id,
            remote_resource_id=remote.resource_id,
            branch="main",
        )

        assert synchronized.status == "degraded"
        assert synchronized.reason_code == "mission_staging_fast_forward_failed"
        assert "git_pull_ff_current_branch_mismatch" in synchronized.violations
        new_calls = runner.calls[before_calls:]
        assert ["git", "fetch", "origin", "main"] in new_calls
        assert ["git", "pull", "--ff-only", "origin", "main"] not in new_calls
    finally:
        shutil.rmtree(staging.parent, ignore_errors=True)


def test_synchronize_without_fetch_pull_authority_is_fail_closed(tmp_path: Path) -> None:
    bare = _bare_repository(tmp_path)
    store = TaskRunStore(root=tmp_path / "task_runs_no_sync")
    contract = _contract(authorize_sync=False)
    parent = _parent(store, contract)
    remote = contract.remote_resources[0]
    service, runner = _service(tmp_path, bare, store)

    materialized = service.materialize(
        parent_run_id=parent.run_id,
        remote_resource_id=remote.resource_id,
        branch="main",
    )
    assert materialized.status == "materialized"
    assert materialized.child_task_run_id
    staging = Path(materialized.workspace_path or "")
    try:
        before_calls = len(runner.calls)
        synchronized = service.synchronize(
            child_run_id=materialized.child_task_run_id,
            remote_resource_id=remote.resource_id,
            branch="main",
        )

        assert synchronized.status == "blocked"
        assert synchronized.reason_code == "mission_staging_git_fetch_not_permitted"
        assert len(runner.calls) == before_calls
    finally:
        shutil.rmtree(staging.parent, ignore_errors=True)
