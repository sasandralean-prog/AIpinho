from __future__ import annotations

from pathlib import Path

from aipinho.schemas.tools.git_command_policy import GitCommandClassification


class GitCommandClassificationService:
    """Classify Git argv without granting authority or executing Git."""

    LOCAL_READ = {
        "status": "git_status",
        "diff": "git_diff",
        "log": "git_log",
        "show": "git_show",
        "rev-parse": "git_rev_parse",
        "ls-files": "git_ls_files",
    }
    NETWORK_READ = {
        "clone": "git_clone",
        "fetch": "git_fetch",
        "ls-remote": "git_ls_remote",
    }
    WORKTREE_WRITE = {
        "checkout": "git_checkout",
        "switch": "git_switch",
        "restore": "git_restore",
        "add": "git_add",
    }

    def classify(self, argv: list[str]) -> GitCommandClassification:
        tokens = [str(item) for item in argv]
        if not tokens or Path(tokens[0].strip('"')).name.lower() not in {"git", "git.exe"}:
            return self._unknown("git_executable_required")
        args = tokens[1:]
        if not args:
            return self._unknown("git_subcommand_required")

        subcommand, subcommand_index = self._subcommand(args)
        if subcommand is None:
            return self._unknown("git_subcommand_required")
        tail = args[subcommand_index + 1 :]
        lowered = [item.casefold() for item in tail]

        destructive_reason = self._destructive_reason(subcommand, lowered)
        if destructive_reason:
            return self._result(
                operation_class="destructive",
                operation=self._destructive_operation(subcommand, lowered),
                capability="git_destructive",
                destructive=True,
                worktree_mutation=True,
                reason_code=destructive_reason,
            )

        if subcommand in self.LOCAL_READ:
            return self._result(
                operation_class="local_read",
                operation=self.LOCAL_READ[subcommand],
                capability="git_local_read",
                reason_code="git_local_read_classified",
                safe_for_governed_execution=True,
            )
        if subcommand == "branch" and self._branch_is_readonly(lowered):
            return self._result(
                operation_class="local_read",
                operation="git_branch_read",
                capability="git_local_read",
                reason_code="git_local_read_classified",
                safe_for_governed_execution=True,
            )
        if subcommand == "remote" and self._remote_is_readonly(lowered):
            return self._result(
                operation_class="local_read",
                operation="git_remote_read",
                capability="git_local_read",
                reason_code="git_local_read_classified",
                safe_for_governed_execution=True,
            )
        if subcommand == "config" and self._config_is_readonly(lowered):
            return self._result(
                operation_class="local_read",
                operation="git_config_read",
                capability="git_local_read",
                reason_code="git_local_read_classified",
                safe_for_governed_execution=True,
            )

        if subcommand in self.NETWORK_READ:
            remote_name, branch = self._network_target(subcommand, tail)
            operation = self.NETWORK_READ[subcommand]
            return self._result(
                operation_class="network_read",
                operation=operation,
                capability=operation,
                capabilities_required=[operation, "outbound_network"],
                network_required=True,
                requires_remote_scope=True,
                worktree_mutation=subcommand == "clone",
                remote_name=remote_name,
                branch=branch,
                reason_code="git_network_read_classified",
                safe_for_governed_execution=True,
            )
        if subcommand == "pull" and "--ff-only" in lowered:
            remote_name, branch = self._remote_and_branch(tail)
            return self._result(
                operation_class="network_read",
                operation="git_pull_ff",
                capability="git_pull_ff",
                capabilities_required=["git_pull_ff", "outbound_network"],
                network_required=True,
                requires_remote_scope=True,
                worktree_mutation=True,
                remote_name=remote_name,
                branch=branch,
                reason_code="git_fast_forward_pull_classified",
                safe_for_governed_execution=True,
            )

        if subcommand in self.WORKTREE_WRITE:
            return self._result(
                operation_class="worktree_write",
                operation=self.WORKTREE_WRITE[subcommand],
                capability="git_worktree_write",
                worktree_mutation=True,
                branch=self._first_positional(tail),
                reason_code="git_worktree_write_classified",
                safe_for_governed_execution=True,
            )
        if subcommand == "commit":
            return self._result(
                operation_class="commit",
                operation="git_commit",
                capability="git_commit",
                requires_remote_scope=True,
                worktree_mutation=True,
                reason_code="git_commit_classified",
                safe_for_governed_execution=True,
            )
        if subcommand == "push":
            remote_name, branch = self._remote_and_branch(tail)
            return self._result(
                operation_class="push",
                operation="git_push",
                capability="git_push",
                capabilities_required=["git_push", "outbound_network"],
                network_required=True,
                requires_remote_scope=True,
                remote_name=remote_name,
                branch=branch,
                reason_code="git_push_classified",
                safe_for_governed_execution=True,
            )
        return self._unknown("git_subcommand_not_governed")

    @staticmethod
    def _subcommand(args: list[str]) -> tuple[str | None, int]:
        index = 0
        while index < len(args):
            token = args[index]
            if token in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
                index += 2
                continue
            if token.startswith(("--git-dir=", "--work-tree=", "--namespace=")):
                index += 1
                continue
            if token.startswith("-"):
                index += 1
                continue
            return token.casefold(), index
        return None, -1

    @staticmethod
    def _destructive_reason(subcommand: str, lowered: list[str]) -> str | None:
        flags = set(lowered)
        if subcommand == "reset":
            return "git_history_or_worktree_reset_denied"
        if subcommand == "clean":
            return "git_clean_denied"
        if subcommand == "push" and flags.intersection({"-f", "--force", "--force-with-lease", "--mirror", "--delete"}):
            return "git_force_or_delete_push_denied"
        if subcommand == "push" and any(item.startswith(":") for item in lowered if not item.startswith("--")):
            return "git_force_or_delete_push_denied"
        if subcommand == "branch" and flags.intersection({"-d", "-D", "--delete"}):
            return "git_branch_delete_denied"
        if subcommand == "commit" and "--amend" in flags:
            return "git_history_rewrite_denied"
        if subcommand == "checkout" and flags.intersection({"-b", "-B"}):
            return "git_branch_reset_or_create_denied"
        if subcommand == "switch" and flags.intersection({"-c", "-C"}):
            return "git_branch_reset_or_create_denied"
        if subcommand in {"rebase", "merge", "cherry-pick", "revert", "rm"}:
            return "git_history_or_destructive_worktree_operation_denied"
        return None

    @staticmethod
    def _destructive_operation(subcommand: str, lowered: list[str]) -> str:
        if subcommand == "push":
            return "git_force_push"
        if subcommand == "branch":
            return "git_branch_delete"
        if subcommand == "clean":
            return "git_clean"
        if subcommand == "reset":
            return "git_history_rewrite"
        if subcommand == "commit" and "--amend" in lowered:
            return "git_history_rewrite"
        return "git_destructive"

    @staticmethod
    def _branch_is_readonly(args: list[str]) -> bool:
        if not args:
            return True
        return not set(args).intersection({"-d", "--delete", "-m", "--move", "-c", "--copy", "-f", "--force"})

    @staticmethod
    def _remote_is_readonly(args: list[str]) -> bool:
        if not args:
            return True
        return args[0] in {"-v", "show", "get-url"}

    @staticmethod
    def _config_is_readonly(args: list[str]) -> bool:
        if not args:
            return False
        return args[0] in {"--get", "--get-all", "--get-regexp", "--list", "-l"}

    def _network_target(self, subcommand: str, args: list[str]) -> tuple[str | None, str | None]:
        positional = self._positionals(args)
        if subcommand == "clone":
            return (positional[0] if positional else None), self._option_value(args, {"-b", "--branch"})
        if subcommand == "ls-remote":
            return (positional[0] if positional else None), (positional[1] if len(positional) > 1 else None)
        return self._remote_and_branch(args)

    def _remote_and_branch(self, args: list[str]) -> tuple[str | None, str | None]:
        positional = self._positionals(args)
        remote = positional[0] if positional else None
        branch = positional[1] if len(positional) > 1 else None
        if branch and ":" in branch:
            source, destination = branch.split(":", 1)
            branch = destination or source or None
        return remote, branch

    @staticmethod
    def _positionals(args: list[str]) -> list[str]:
        result: list[str] = []
        skip_next = False
        options_with_values = {"-b", "--branch", "--depth", "--filter", "--upload-pack", "--receive-pack"}
        for token in args:
            if skip_next:
                skip_next = False
                continue
            if token in options_with_values:
                skip_next = True
                continue
            if token.startswith("-"):
                continue
            result.append(token)
        return result

    @staticmethod
    def _option_value(args: list[str], names: set[str]) -> str | None:
        for index, token in enumerate(args):
            if token in names and index + 1 < len(args):
                return args[index + 1]
            for name in names:
                prefix = f"{name}="
                if token.startswith(prefix):
                    return token[len(prefix) :]
        return None

    def _first_positional(self, args: list[str]) -> str | None:
        positional = self._positionals(args)
        return positional[0] if positional else None

    def _unknown(self, reason: str) -> GitCommandClassification:
        return self._result(
            operation_class="unknown",
            operation="git_unknown",
            capability="git_unknown",
            reason_code=reason,
        )

    @staticmethod
    def _result(**kwargs) -> GitCommandClassification:
        capability = str(kwargs.get("capability") or "git_unknown")
        capabilities = list(kwargs.pop("capabilities_required", []) or [capability])
        return GitCommandClassification(
            capabilities_required=capabilities,
            **kwargs,
        )
