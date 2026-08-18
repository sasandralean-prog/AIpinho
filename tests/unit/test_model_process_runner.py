from __future__ import annotations

import sys

from aipinho.services.models.model_process_runner import ModelProcessRunner


def _runner(config: dict | None = None) -> ModelProcessRunner:
    return ModelProcessRunner(
        config=config
        or {
            "process": {
                "use_shell": False,
                "allow_env_override": False,
                "isolate_process_group": True,
                "no_window": True,
                "kill_child_on_timeout": True,
                "kill_process_tree_on_timeout": False,
                "encoding": "utf-8",
                "errors": "replace",
            }
        }
    )


def test_model_process_runner_completed_command_does_not_kill_parent() -> None:
    result = _runner().run(
        [sys.executable, "-c", "print('runner_ok')"],
        timeout_seconds=5,
        max_stdout_chars=1000,
        max_stderr_chars=1000,
    )
    assert result.status == "completed"
    assert result.returncode == 0
    assert "runner_ok" in result.stdout
    assert result.killed is False


def test_model_process_runner_nonzero_command_is_controlled_error() -> None:
    result = _runner().run(
        [sys.executable, "-c", "import sys; print('before_exit'); sys.exit(7)"],
        timeout_seconds=5,
        max_stdout_chars=1000,
        max_stderr_chars=1000,
    )
    assert result.status == "error"
    assert result.returncode == 7
    assert "before_exit" in result.stdout
    assert result.killed is False


def test_model_process_runner_timeout_kills_only_child() -> None:
    result = _runner().run(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout_seconds=1,
        max_stdout_chars=1000,
        max_stderr_chars=1000,
    )
    assert result.status == "timeout"
    assert result.timed_out is True
    assert result.killed is True
    assert result.cancellation_reason == "timeout_child_killed"


def test_model_process_runner_missing_executable_is_controlled_error() -> None:
    result = _runner().run(
        ["missing-aipinho-model-runtime-executable.exe"],
        timeout_seconds=5,
        max_stdout_chars=1000,
        max_stderr_chars=1000,
    )
    assert result.status == "error"
    assert result.stderr == "executable_not_found"
    assert result.returncode is None


def test_model_process_runner_shell_policy_blocked() -> None:
    result = _runner({"process": {"use_shell": True}}).run(
        [sys.executable, "-c", "print('nope')"],
        timeout_seconds=5,
        max_stdout_chars=1000,
        max_stderr_chars=1000,
    )
    assert result.status == "blocked"
    assert result.stderr == "shell_execution_blocked"


def test_model_process_runner_status_exposes_windows_isolation_policy() -> None:
    status = _runner().status()
    assert status["isolate_process_group"] is True
    assert status["no_window"] is True
    assert status["kill_child_on_timeout"] is True
    assert status["kill_process_tree_on_timeout"] is False
