from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.gemini_executor import GeminiExecutorConfigStatus
from aipinho.utils.yaml_loader import load_yaml_file


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _append_key(keys: list[str], value: str | None) -> None:
    if value is None:
        return
    key = value.strip()
    if key and key not in keys:
        keys.append(key)


def _collect_api_keys() -> tuple[str, ...]:
    keys: list[str] = []
    _append_key(keys, os.getenv("GEMINI_API_KEY_PRIMARY") or os.getenv("GEMINI_API_KEY"))
    _append_key(keys, os.getenv("GEMINI_API_KEY_SECONDARY"))
    for index in range(1, 21):
        _append_key(keys, os.getenv(f"GEMINI_API_KEY_FALLBACK_{index}"))
    list_value = os.getenv("GEMINI_API_KEYS")
    if list_value:
        for value in list_value.replace(";", ",").split(","):
            _append_key(keys, value)
    return tuple(keys)


@dataclass(frozen=True)
class GeminiExecutorRuntimeConfig:
    enabled: bool
    default_model: str
    default_execution_mode: str
    timeout_seconds: int
    max_prompt_chars: int
    max_output_chars: int
    allow_write: bool
    allow_shell: bool
    require_approval_for_write: bool
    require_approval_for_shell: bool
    use_memory_gateway: bool
    use_delegation: bool
    prefer_aipinho_executor: bool
    allow_direct_local_tools: bool
    autorun_enabled: bool
    autoreview_enabled: bool
    autoapproval_enabled: bool
    raw_default_visible: bool
    cloud_warning_visible: bool
    api_keys: tuple[str, ...]
    primary_key: str | None
    secondary_key: str | None


class GeminiExecutorConfigService:
    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or PATHS.config_root / "gemini_executor" / "gemini_executor_policy.yaml"

    def policy(self) -> dict[str, Any]:
        if not self.policy_path.exists():
            return {}
        return load_yaml_file(self.policy_path, root=PATHS.project_root)

    def runtime(self) -> GeminiExecutorRuntimeConfig:
        policy = self.policy()
        defaults = dict(policy.get("runtime_defaults") or {})
        api_keys = _collect_api_keys()
        return GeminiExecutorRuntimeConfig(
            enabled=_as_bool(os.getenv("GEMINI_AGENT_ENABLED") or os.getenv("GEMINI_EXECUTOR_ENABLED"), bool(defaults.get("enabled", False))),
            default_model=os.getenv("GEMINI_AGENT_DEFAULT_MODEL") or os.getenv("GEMINI_EXECUTOR_DEFAULT_MODEL") or str(defaults.get("default_model", "gemini-2.5-flash")),
            default_execution_mode=os.getenv("GEMINI_AGENT_DEFAULT_EXECUTION_MODE") or str(defaults.get("default_execution_mode", "governed_autorun")),
            timeout_seconds=_as_int(os.getenv("GEMINI_AGENT_TIMEOUT_SECONDS") or os.getenv("GEMINI_EXECUTOR_TIMEOUT_SECONDS"), int(defaults.get("timeout_seconds", 90))),
            max_prompt_chars=_as_int(os.getenv("GEMINI_AGENT_MAX_PROMPT_CHARS") or os.getenv("GEMINI_EXECUTOR_MAX_PROMPT_CHARS"), int(defaults.get("max_prompt_chars", 200000))),
            max_output_chars=_as_int(os.getenv("GEMINI_AGENT_MAX_OUTPUT_CHARS") or os.getenv("GEMINI_EXECUTOR_MAX_OUTPUT_CHARS"), int(defaults.get("max_output_chars", 65536))),
            allow_write=_as_bool(os.getenv("GEMINI_EXECUTOR_ALLOW_WRITE"), bool(defaults.get("allow_write", False))),
            allow_shell=_as_bool(os.getenv("GEMINI_EXECUTOR_ALLOW_SHELL"), bool(defaults.get("allow_shell", False))),
            require_approval_for_write=_as_bool(
                os.getenv("GEMINI_EXECUTOR_REQUIRE_APPROVAL_FOR_WRITE"),
                bool(defaults.get("require_approval_for_write", True)),
            ),
            require_approval_for_shell=_as_bool(
                os.getenv("GEMINI_EXECUTOR_REQUIRE_APPROVAL_FOR_SHELL"),
                bool(defaults.get("require_approval_for_shell", True)),
            ),
            use_memory_gateway=_as_bool(os.getenv("GEMINI_AGENT_USE_MEMORY_GATEWAY"), bool(defaults.get("use_memory_gateway", True))),
            use_delegation=_as_bool(os.getenv("GEMINI_AGENT_USE_DELEGATION"), bool(defaults.get("use_delegation", True))),
            prefer_aipinho_executor=_as_bool(os.getenv("GEMINI_AGENT_PREFER_AIPINHO_EXECUTOR"), bool(defaults.get("prefer_aipinho_executor", True))),
            allow_direct_local_tools=_as_bool(os.getenv("GEMINI_AGENT_ALLOW_DIRECT_LOCAL_TOOLS"), bool(defaults.get("allow_direct_local_tools", False))),
            autorun_enabled=_as_bool(os.getenv("GEMINI_AGENT_AUTORUN_ENABLED"), bool(defaults.get("autorun_enabled", True))),
            autoreview_enabled=_as_bool(os.getenv("GEMINI_AGENT_AUTOREVIEW_ENABLED"), bool(defaults.get("autoreview_enabled", True))),
            autoapproval_enabled=_as_bool(os.getenv("GEMINI_AGENT_AUTOAPPROVAL_ENABLED"), bool(defaults.get("autoapproval_enabled", True))),
            raw_default_visible=_as_bool(os.getenv("GEMINI_AGENT_RAW_DEFAULT_VISIBLE"), bool(defaults.get("raw_default_visible", False))),
            cloud_warning_visible=_as_bool(os.getenv("GEMINI_AGENT_CLOUD_WARNING_VISIBLE"), bool(defaults.get("cloud_warning_visible", True))),
            api_keys=api_keys,
            primary_key=api_keys[0] if api_keys else None,
            secondary_key=api_keys[1] if len(api_keys) > 1 else None,
        )

    def status(self, *, last_error_sanitized: str | None = None) -> GeminiExecutorConfigStatus:
        config = self.runtime()
        return GeminiExecutorConfigStatus(
            enabled=config.enabled,
            primary_key_configured=bool(config.primary_key),
            secondary_key_configured=bool(config.secondary_key),
            configured_key_count=len(config.api_keys),
            fallback_key_count_configured=max(0, len(config.api_keys) - 2),
            default_model=config.default_model,
            default_execution_mode=config.default_execution_mode,
            timeout_seconds=config.timeout_seconds,
            max_prompt_chars=config.max_prompt_chars,
            max_output_chars=config.max_output_chars,
            allow_write=config.allow_write,
            allow_shell=config.allow_shell,
            require_approval_for_write=config.require_approval_for_write,
            require_approval_for_shell=config.require_approval_for_shell,
            use_memory_gateway=config.use_memory_gateway,
            use_delegation=config.use_delegation,
            prefer_aipinho_executor=config.prefer_aipinho_executor,
            allow_direct_local_tools=config.allow_direct_local_tools,
            autorun_enabled=config.autorun_enabled,
            autoreview_enabled=config.autoreview_enabled,
            autoapproval_enabled=config.autoapproval_enabled,
            raw_default_visible=config.raw_default_visible,
            cloud_warning_visible=config.cloud_warning_visible,
            last_error_sanitized=last_error_sanitized,
        )
