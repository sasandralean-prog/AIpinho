from __future__ import annotations

import pytest

from aipinho.services.tools.git_command_classification_service import (
    GitCommandClassificationService,
)
from aipinho.services.tools.shell_command_policy_service import ShellCommandPolicyService


@pytest.mark.parametrize(
    ("argv", "operation", "capability"),
    [
        (["git", "status"], "git_status", "git_local_read"),
        (["git", "diff", "--stat"], "git_diff", "git_local_read"),
        (["git", "log", "-1"], "git_log", "git_local_read"),
        (["git", "rev-parse", "HEAD"], "git_rev_parse", "git_local_read"),
        (["git", "branch", "--show-current"], "git_branch_read", "git_local_read"),
        (["git", "remote", "get-url", "origin"], "git_remote_read", "git_local_read"),
    ],
)
def test_local_git_reads_are_classified_without_network(argv, operation, capability) -> None:
    result = GitCommandClassificationService().classify(argv)

    assert result.operation_class == "local_read"
    assert result.operation == operation
    assert result.capability == capability
    assert result.network_required is False
    assert result.safe_for_governed_execution is True


@pytest.mark.parametrize(
    ("argv", "operation", "remote", "branch"),
    [
        (["git", "fetch", "origin", "main"], "git_fetch", "origin", "main"),
        (["git", "ls-remote", "origin", "main"], "git_ls_remote", "origin", "main"),
        (["git", "clone", "--branch", "main", "https://code.example.test/team/app.git"], "git_clone", "https://code.example.test/team/app.git", "main"),
        (["git", "pull", "--ff-only", "origin", "main"], "git_pull_ff", "origin", "main"),
    ],
)
def test_network_git_reads_expose_remote_scope_demand(argv, operation, remote, branch) -> None:
    result = GitCommandClassificationService().classify(argv)

    assert result.operation_class == "network_read"
    assert result.operation == operation
    assert result.capability == operation
    assert result.network_required is True
    assert result.requires_remote_scope is True
    assert result.remote_name == remote
    assert result.branch == branch
    assert "outbound_network" in result.capabilities_required


def test_commit_and_push_are_distinct_capabilities() -> None:
    service = GitCommandClassificationService()
    commit = service.classify(["git", "commit", "-m", "message"])
    push = service.classify(["git", "push", "origin", "main"])

    assert (commit.operation_class, commit.capability) == ("commit", "git_commit")
    assert (push.operation_class, push.capability) == ("push", "git_push")
    assert push.network_required and push.requires_remote_scope


@pytest.mark.parametrize(
    "argv",
    [
        ["git", "reset", "--hard", "HEAD~1"],
        ["git", "clean", "-fd"],
        ["git", "push", "--force", "origin", "main"],
        ["git", "push", "-f", "origin", "main"],
        ["git", "branch", "-D", "old"],
        ["git", "commit", "--amend", "-m", "rewrite"],
        ["git", "rebase", "main"],
    ],
)
def test_destructive_git_paths_are_fail_closed(argv) -> None:
    result = GitCommandClassificationService().classify(argv)

    assert result.operation_class == "destructive"
    assert result.capability == "git_destructive"
    assert result.destructive is True
    assert result.safe_for_governed_execution is False


def test_worktree_change_is_distinct_from_commit_and_destructive_git() -> None:
    result = GitCommandClassificationService().classify(["git", "checkout", "feature/topic"])

    assert result.operation_class == "worktree_write"
    assert result.operation == "git_checkout"
    assert result.capability == "git_worktree_write"
    assert result.worktree_mutation is True
    assert result.destructive is False


def test_unknown_git_subcommand_remains_fail_closed() -> None:
    result = GitCommandClassificationService().classify(["git", "worktree", "add", "../other"])

    assert result.operation_class == "unknown"
    assert result.safe_for_governed_execution is False
    assert result.reason_code == "git_subcommand_not_governed"


def test_shell_policy_projects_granular_git_into_legacy_fail_closed_boundary() -> None:
    service = ShellCommandPolicyService()
    status = service.classify(argv=["git", "status"], working_dir=r"C:\tmp\repo")
    fetch = service.classify(argv=["git", "fetch", "origin", "main"], working_dir=r"C:\tmp\repo")
    push = service.classify(argv=["git", "push", "origin", "main"], working_dir=r"C:\tmp\repo")
    force = service.classify(argv=["git", "push", "--force", "origin", "main"], working_dir=r"C:\tmp\repo")

    assert status.category == "git_read_shell" and status.policy_decision == "allowed"
    assert fetch.category == "git_write_shell" and fetch.policy_decision == "blocked"
    assert push.category == "git_write_shell" and push.policy_decision == "blocked"
    assert force.category == "git_write_shell" and force.policy_decision == "blocked"
    assert fetch.git_classification and fetch.git_classification.operation == "git_fetch"
    assert push.git_classification and push.git_classification.capability == "git_push"
    assert force.git_classification and force.git_classification.destructive is True
