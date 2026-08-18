from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.codex_agent import CodexAgentConfigStatus
from aipinho.utils.yaml_loader import load_yaml_file


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value or "")
    except ValueError:
        return default


@dataclass(frozen=True)
class CodexAgentRuntimeConfig:
    enabled: bool
    cli_path: str
    default_workdir: str
    timeout_seconds: int
    require_approval_for_write: bool
    require_approval_for_shell: bool
    allow_read: bool
    allow_write: bool
    allow_shell: bool
    use_staging_worktree: bool
    max_output_chars: int
    history_retention_days: int
    history_context_messages: int
    history_context_chars: int
    mobile_enabled: bool = True
    autorun_enabled: bool = True
    autoreview_enabled: bool = True
    autoapproval_enabled: bool = True
    autopilot_mode: str = "governed_autorun"
    polling_interval_seconds: int = 5
    max_run_seconds: int = 1800
    max_shell_seconds: int = 600
    max_events_per_poll: int = 100
    max_output_chars_per_event: int = 12000
    allow_artifact_upload: bool = True
    allow_artifact_download: bool = True
    auto_approve_read: bool = True
    auto_approve_artifact_upload: bool = True
    auto_approve_artifact_download: bool = True
    auto_approve_write_in_target_mutable: bool = True
    auto_approve_readonly_shell: bool = True
    auto_approve_test_shell: bool = True
    auto_approve_build_shell: bool = True
    auto_approve_destructive_shell: bool = False
    auto_approve_git_write: bool = False
    auto_approve_network_shell: bool = False
    auto_approve_process_control: bool = False
    auto_approve_forbidden_workspace: bool = False
    require_human_for_high_risk: bool = True
    emergency_stop_enabled: bool = True
    autorun_max_steps: int = 20
    autorun_max_file_writes: int = 50
    autorun_max_shell_commands: int = 20
    autorun_max_artifacts: int = 20


class CodexAgentConfigService:
    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or PATHS.config_root / "codex_agent" / "codex_agent_policy.yaml"

    def policy(self) -> dict:
        if not self.policy_path.exists():
            return {}
        return load_yaml_file(self.policy_path, root=PATHS.project_root)

    def runtime(self) -> CodexAgentRuntimeConfig:
        defaults = dict((self.policy().get("runtime_defaults") or {}))
        return CodexAgentRuntimeConfig(
            enabled=_as_bool(os.getenv("CODEX_AGENT_ENABLED"), bool(defaults.get("enabled", False))),
            cli_path=os.getenv("CODEX_AGENT_CLI_PATH") or str(defaults.get("cli_path", "codex")),
            default_workdir=os.getenv("CODEX_AGENT_DEFAULT_WORKDIR") or str(defaults.get("default_workdir", PATHS.project_root)),
            timeout_seconds=_as_int(os.getenv("CODEX_AGENT_TIMEOUT_SECONDS"), int(defaults.get("timeout_seconds", 600))),
            require_approval_for_write=_as_bool(os.getenv("CODEX_AGENT_REQUIRE_APPROVAL_FOR_WRITE"), bool(defaults.get("require_approval_for_write", True))),
            require_approval_for_shell=_as_bool(os.getenv("CODEX_AGENT_REQUIRE_APPROVAL_FOR_SHELL"), bool(defaults.get("require_approval_for_shell", True))),
            allow_read=_as_bool(os.getenv("CODEX_AGENT_ALLOW_READ"), bool(defaults.get("allow_read", True))),
            allow_write=_as_bool(os.getenv("CODEX_AGENT_ALLOW_WRITE"), bool(defaults.get("allow_write", False))),
            allow_shell=_as_bool(os.getenv("CODEX_AGENT_ALLOW_SHELL"), bool(defaults.get("allow_shell", False))),
            use_staging_worktree=_as_bool(os.getenv("CODEX_AGENT_USE_STAGING_WORKTREE"), bool(defaults.get("use_staging_worktree", True))),
            max_output_chars=_as_int(os.getenv("CODEX_AGENT_MAX_OUTPUT_CHARS"), int(defaults.get("max_output_chars", 200000))),
            history_retention_days=_as_int(os.getenv("CODEX_AGENT_HISTORY_RETENTION_DAYS"), int(defaults.get("history_retention_days", 90))),
            history_context_messages=_as_int(os.getenv("CODEX_AGENT_HISTORY_CONTEXT_MESSAGES"), int(defaults.get("history_context_messages", 20))),
            history_context_chars=_as_int(os.getenv("CODEX_AGENT_HISTORY_CONTEXT_CHARS"), int(defaults.get("history_context_chars", 24000))),
            mobile_enabled=_as_bool(os.getenv("CODEX_AGENT_MOBILE_ENABLED"), bool(defaults.get("mobile_enabled", True))),
            autorun_enabled=_as_bool(os.getenv("CODEX_AGENT_AUTORUN_ENABLED"), bool(defaults.get("autorun_enabled", True))),
            autoreview_enabled=_as_bool(os.getenv("CODEX_AGENT_AUTOREVIEW_ENABLED"), bool(defaults.get("autoreview_enabled", True))),
            autoapproval_enabled=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVAL_ENABLED"), bool(defaults.get("autoapproval_enabled", True))),
            autopilot_mode=os.getenv("CODEX_AGENT_AUTOPILOT_MODE") or str(defaults.get("autopilot_mode", "governed_autorun")),
            polling_interval_seconds=_as_int(os.getenv("CODEX_AGENT_POLLING_INTERVAL_SECONDS"), int(defaults.get("polling_interval_seconds", 5))),
            max_run_seconds=_as_int(os.getenv("CODEX_AGENT_MAX_RUN_SECONDS"), int(defaults.get("max_run_seconds", 1800))),
            max_shell_seconds=_as_int(os.getenv("CODEX_AGENT_MAX_SHELL_SECONDS"), int(defaults.get("max_shell_seconds", 600))),
            max_events_per_poll=_as_int(os.getenv("CODEX_AGENT_MAX_EVENTS_PER_POLL"), int(defaults.get("max_events_per_poll", 100))),
            max_output_chars_per_event=_as_int(os.getenv("CODEX_AGENT_MAX_OUTPUT_CHARS_PER_EVENT"), int(defaults.get("max_output_chars_per_event", 12000))),
            allow_artifact_upload=_as_bool(os.getenv("CODEX_AGENT_ALLOW_ARTIFACT_UPLOAD"), bool(defaults.get("allow_artifact_upload", True))),
            allow_artifact_download=_as_bool(os.getenv("CODEX_AGENT_ALLOW_ARTIFACT_DOWNLOAD"), bool(defaults.get("allow_artifact_download", True))),
            auto_approve_read=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_READ"), bool(defaults.get("auto_approve_read", True))),
            auto_approve_artifact_upload=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_ARTIFACT_UPLOAD"), bool(defaults.get("auto_approve_artifact_upload", True))),
            auto_approve_artifact_download=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_ARTIFACT_DOWNLOAD"), bool(defaults.get("auto_approve_artifact_download", True))),
            auto_approve_write_in_target_mutable=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_WRITE_IN_TARGET_MUTABLE"), bool(defaults.get("auto_approve_write_in_target_mutable", True))),
            auto_approve_readonly_shell=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_READONLY_SHELL"), bool(defaults.get("auto_approve_readonly_shell", True))),
            auto_approve_test_shell=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_TEST_SHELL"), bool(defaults.get("auto_approve_test_shell", True))),
            auto_approve_build_shell=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_BUILD_SHELL"), bool(defaults.get("auto_approve_build_shell", True))),
            auto_approve_destructive_shell=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_DESTRUCTIVE_SHELL"), bool(defaults.get("auto_approve_destructive_shell", False))),
            auto_approve_git_write=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_GIT_WRITE"), bool(defaults.get("auto_approve_git_write", False))),
            auto_approve_network_shell=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_NETWORK_SHELL"), bool(defaults.get("auto_approve_network_shell", False))),
            auto_approve_process_control=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_PROCESS_CONTROL"), bool(defaults.get("auto_approve_process_control", False))),
            auto_approve_forbidden_workspace=_as_bool(os.getenv("CODEX_AGENT_AUTO_APPROVE_FORBIDDEN_WORKSPACE"), bool(defaults.get("auto_approve_forbidden_workspace", False))),
            require_human_for_high_risk=_as_bool(os.getenv("CODEX_AGENT_REQUIRE_HUMAN_FOR_HIGH_RISK"), bool(defaults.get("require_human_for_high_risk", True))),
            emergency_stop_enabled=_as_bool(os.getenv("CODEX_AGENT_EMERGENCY_STOP_ENABLED"), bool(defaults.get("emergency_stop_enabled", True))),
            autorun_max_steps=_as_int(os.getenv("CODEX_AGENT_AUTORUN_MAX_STEPS"), int(defaults.get("autorun_max_steps", 20))),
            autorun_max_file_writes=_as_int(os.getenv("CODEX_AGENT_AUTORUN_MAX_FILE_WRITES"), int(defaults.get("autorun_max_file_writes", 50))),
            autorun_max_shell_commands=_as_int(os.getenv("CODEX_AGENT_AUTORUN_MAX_SHELL_COMMANDS"), int(defaults.get("autorun_max_shell_commands", 20))),
            autorun_max_artifacts=_as_int(os.getenv("CODEX_AGENT_AUTORUN_MAX_ARTIFACTS"), int(defaults.get("autorun_max_artifacts", 20))),
        )

    def status(self) -> CodexAgentConfigStatus:
        config = self.runtime()
        detected, cli_status, error = self.detect_cli(config.cli_path)
        return CodexAgentConfigStatus(
            enabled=config.enabled,
            cli_path=config.cli_path,
            cli_detected=detected,
            cli_status=cli_status,
            default_workdir=config.default_workdir,
            timeout_seconds=config.timeout_seconds,
            require_approval_for_write=config.require_approval_for_write,
            require_approval_for_shell=config.require_approval_for_shell,
            allow_read=config.allow_read,
            allow_write=config.allow_write,
            allow_shell=config.allow_shell,
            use_staging_worktree=config.use_staging_worktree,
            max_output_chars=config.max_output_chars,
            history_retention_days=config.history_retention_days,
            history_context_messages=config.history_context_messages,
            history_context_chars=config.history_context_chars,
            mobile_enabled=config.mobile_enabled,
            autorun_enabled=config.autorun_enabled,
            autoreview_enabled=config.autoreview_enabled,
            autoapproval_enabled=config.autoapproval_enabled,
            autopilot_mode=config.autopilot_mode,
            polling_interval_seconds=config.polling_interval_seconds,
            max_run_seconds=config.max_run_seconds,
            max_shell_seconds=config.max_shell_seconds,
            max_events_per_poll=config.max_events_per_poll,
            max_output_chars_per_event=config.max_output_chars_per_event,
            allow_artifact_upload=config.allow_artifact_upload,
            allow_artifact_download=config.allow_artifact_download,
            autorun_max_steps=config.autorun_max_steps,
            autorun_max_file_writes=config.autorun_max_file_writes,
            autorun_max_shell_commands=config.autorun_max_shell_commands,
            autorun_max_artifacts=config.autorun_max_artifacts,
            emergency_stop_enabled=config.emergency_stop_enabled,
            last_error_sanitized=error,
        )

    def detect_cli(self, cli_path: str) -> tuple[bool, str, str | None]:
        resolved = shutil.which(cli_path) if cli_path == "codex" else cli_path
        if not resolved:
            return False, "missing_cli", None
        try:
            completed = subprocess.run([resolved, "--help"], capture_output=True, text=True, timeout=5, check=False)
        except PermissionError:
            return True, "cli_inaccessible", "permission_denied"
        except subprocess.TimeoutExpired:
            return True, "cli_timeout", "timeout"
        except Exception:
            return True, "cli_probe_failed", "probe_failed"
        if completed.returncode == 0:
            return True, "ready_or_help_available", None
        return True, "cli_present_but_unhealthy", f"exit_{completed.returncode}"
