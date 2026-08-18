from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ProcessResult:
    status: str
    stdout: str
    stderr: str
    returncode: int | None
    timed_out: bool = False
    killed: bool = False
    latency_ms: int = 0
    cancellation_reason: str | None = None
    creationflags_used: int = 0


class ModelProcessRunner:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "security" / "model_process_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: int,
        max_stdout_chars: int,
        max_stderr_chars: int,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> ProcessResult:
        policy = self.config.get("process", {}) if isinstance(self.config.get("process", {}), dict) else {}
        if policy.get("use_shell", False):
            return ProcessResult(status="blocked", stdout="", stderr="shell_execution_blocked", returncode=None)
        if not argv:
            return ProcessResult(status="blocked", stdout="", stderr="argv_required", returncode=None)
        if timeout_seconds <= 0:
            return ProcessResult(status="blocked", stdout="", stderr="timeout_required", returncode=None)

        creationflags = self._creationflags(policy)
        started = perf_counter()
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                argv,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding=str(policy.get("encoding") or "utf-8"),
                errors=str(policy.get("errors") or "replace"),
                cwd=cwd,
                env=env,
                creationflags=creationflags,
            )
            stdout, stderr = process.communicate(timeout=timeout_seconds)
            latency_ms = int((perf_counter() - started) * 1000)
            status = "completed" if process.returncode == 0 else "error"
            return ProcessResult(
                status=status,
                stdout=(stdout or "")[:max_stdout_chars],
                stderr=(stderr or "")[:max_stderr_chars],
                returncode=process.returncode,
                latency_ms=latency_ms,
                creationflags_used=creationflags,
            )
        except subprocess.TimeoutExpired:
            latency_ms = int((perf_counter() - started) * 1000)
            stdout = ""
            stderr = "model_process_timeout"
            if process is not None:
                try:
                    process.kill()
                    out, err = process.communicate(timeout=5)
                    stdout = out or ""
                    stderr = err or stderr
                except Exception as exc:
                    stderr = f"{stderr}; kill_cleanup_error={type(exc).__name__}"
            return ProcessResult(
                status="timeout",
                stdout=stdout[:max_stdout_chars],
                stderr=stderr[:max_stderr_chars],
                returncode=process.returncode if process is not None else None,
                timed_out=True,
                killed=True,
                latency_ms=latency_ms,
                cancellation_reason="timeout_child_killed",
                creationflags_used=creationflags,
            )
        except FileNotFoundError:
            latency_ms = int((perf_counter() - started) * 1000)
            return ProcessResult(status="error", stdout="", stderr="executable_not_found", returncode=None, latency_ms=latency_ms, creationflags_used=creationflags)
        except PermissionError:
            latency_ms = int((perf_counter() - started) * 1000)
            return ProcessResult(status="error", stdout="", stderr="permission_denied", returncode=None, latency_ms=latency_ms, creationflags_used=creationflags)
        except OSError as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            return ProcessResult(status="error", stdout="", stderr=f"os_error:{type(exc).__name__}:{str(exc)[:500]}", returncode=None, latency_ms=latency_ms, creationflags_used=creationflags)

    def _creationflags(self, policy: dict[str, Any]) -> int:
        if not sys.platform.startswith("win"):
            return 0
        flags = 0
        if bool(policy.get("isolate_process_group", True)):
            flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        if bool(policy.get("no_window", True)):
            flags |= subprocess.CREATE_NO_WINDOW
        return flags

    def status(self) -> dict[str, object]:
        process = self.config.get("process", {}) if isinstance(self.config.get("process", {}), dict) else {}
        return {
            "status": "ok",
            "service": "model_process_runner",
            "use_shell": bool(process.get("use_shell", False)),
            "allow_env_override": bool(process.get("allow_env_override", False)),
            "isolate_process_group": bool(process.get("isolate_process_group", True)),
            "no_window": bool(process.get("no_window", True)),
            "kill_child_on_timeout": bool(process.get("kill_child_on_timeout", True)),
            "kill_process_tree_on_timeout": bool(process.get("kill_process_tree_on_timeout", False)),
        }
