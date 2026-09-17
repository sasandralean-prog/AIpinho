from __future__ import annotations

from pathlib import Path

from aipinho.schemas.governance.lifecycle import CanonicalPermission
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.task_run_guard import TaskRunGuard
from aipinho.services.tools.shell_command_policy_service import ShellCommandPolicyService
from tests.support.runtime_fixtures import runtime_run
from tests.unit.test_m6_governed_git_execution import _contract


def _shell_plan(command: str, workspace: str) -> dict[str, object]:
    service = object.__new__(CanonicalPublicChatService)
    service.shell_policy = ShellCommandPolicyService()
    return service._shell_plan(workspace, f"command: {command}")


def test_public_shell_plan_freezes_granular_git_classification(tmp_path: Path) -> None:
    workspace = str(tmp_path / "repo")
    plan = _shell_plan("git push origin main", workspace)

    assert plan["shell_category"] == "git_push_shell"
    git_info = plan["git_classification"]
    assert isinstance(git_info, dict)
    assert git_info["operation"] == "git_push"
    assert git_info["capability"] == "git_push"
    assert git_info["branch"] == "main"


def _guard_run(target: Path, contract, command: str):
    run = runtime_run(
        action="run_command",
        contract_type="shell_execution",
        operation_type="run_command",
        runtime_profile="shell",
        workspace=str(target),
        policy={
            "status": "needs_approval",
            "allowed_actions": ["run_command"],
            "denied_actions": [],
            "approval_required_for": ["run_command"],
        },
    )
    run.mission_contract = contract
    run.mission_binding = contract.binding()
    run.intent_map = {
        "intent_type": "run_command",
        "shell_plan": _shell_plan(command, str(target)),
    }
    return run


def test_task_run_guard_uses_remote_git_capability_and_mission_authority(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    contract = _contract(target)
    guard = TaskRunGuard(authority_grants=AuthorityGrantService(store_dir=tmp_path / "grants"))
    decision = guard.check_run(_guard_run(target, contract, "git push origin main"))
    canonical = next(
        item for item in decision.canonical_policy_decisions
        if item.capability == "git_push"
    )

    assert decision.allowed is True
    assert canonical.permission == CanonicalPermission.ALLOWED
    authority = next(item for item in canonical.facets if item.facet == "human_authority")
    assert authority.source == "mission_authority_grant"
    assert authority.details["repository_identity"] == "code.example.test/team/app"
    assert authority.details["branch"] == "main"


def test_task_run_guard_denies_destructive_git_even_with_other_git_authority(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    contract = _contract(target)
    guard = TaskRunGuard(authority_grants=AuthorityGrantService(store_dir=tmp_path / "grants"))

    decision = guard.check_run(
        _guard_run(target, contract, "git push --force origin main")
    )
    canonical = next(
        item for item in decision.canonical_policy_decisions
        if item.capability == "git_destructive"
    )

    assert decision.allowed is False
    assert canonical.permission == CanonicalPermission.DENIED
    assert any(item.reason_code == "git_destructive_operation_denied" for item in canonical.facets)
