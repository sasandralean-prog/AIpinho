from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aipinho.core.local_environment import load_local_environment
from aipinho.core.paths import PATHS
from aipinho.schemas.lucio_agent import LucioConfigStatus
from aipinho.utils.yaml_loader import load_yaml_file


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value
    return None


@dataclass(frozen=True)
class LucioRuntimeConfig:
    enabled: bool
    provider: str
    openai_enabled: bool
    api_key: str | None
    base_url: str | None
    project: str | None
    organization: str | None
    default_model: str
    timeout_seconds: int
    max_prompt_chars: int
    max_output_chars: int
    use_memory_gateway: bool
    use_delegation: bool
    default_execution_mode: str
    allow_direct_local_tools: bool
    raw_default_visible: bool
    multimodal_enabled: bool
    multimodal_provider: str
    multimodal_allowed_content_types: list[str]
    multimodal_store_images: bool
    multimodal_memory_write_default: bool
    multimodal_redaction_required: bool
    multimodal_delegation_enabled: bool
    visible_in_ux: bool
    allow_new_sessions: bool


class LucioAgentConfigService:
    def __init__(
        self,
        policy_path: Path | None = None,
        *,
        load_environment: bool = True,
    ) -> None:
        self.policy_path = policy_path or PATHS.config_root / "agents" / "lucio_agent_policy.yaml"
        self.load_environment = load_environment

    def policy(self) -> dict[str, Any]:
        if not self.policy_path.exists():
            return {}
        return load_yaml_file(self.policy_path, root=PATHS.project_root)

    def runtime(self) -> LucioRuntimeConfig:
        if self.load_environment:
            load_local_environment()
        defaults = dict(self.policy().get("runtime_defaults") or {})
        multimodal = dict(self.policy().get("multimodal") or {})
        allowed_content_types = os.getenv("LUCIO_MULTIMODAL_ALLOWED_CONTENT_TYPES")
        lucio_enabled = _as_bool(_first_env("LUCIO_ENABLED", "LUCIO_AGENT_ENABLED"), bool(defaults.get("enabled", False)))
        openai_enabled = _as_bool(_first_env("LUCIO_OPENAI_ENABLED", "OPENAI_ENABLED"), bool(defaults.get("openai_enabled", False)))
        configured_provider = (_first_env("LUCIO_PROVIDER") or str(defaults.get("provider", "disabled"))).strip().lower()
        effective_provider = configured_provider if lucio_enabled and openai_enabled and configured_provider != "disabled" else "disabled"
        api_key = os.getenv("OPENAI_API_KEY") if effective_provider == "openai" else None
        return LucioRuntimeConfig(
            enabled=lucio_enabled and effective_provider != "disabled",
            provider=effective_provider,
            openai_enabled=openai_enabled,
            api_key=api_key,
            base_url=(
                os.getenv("LUCIO_OPENAI_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or os.getenv("OPENAI_API_BASE")
                or None
            ),
            project=(
                os.getenv("LUCIO_OPENAI_PROJECT")
                or os.getenv("OPENAI_PROJECT")
                or os.getenv("OPENAI_PROJECT_ID")
                or None
            ),
            organization=(
                os.getenv("LUCIO_OPENAI_ORGANIZATION")
                or os.getenv("OPENAI_ORGANIZATION")
                or os.getenv("OPENAI_ORG_ID")
                or None
            ),
            default_model=os.getenv("LUCIO_AGENT_DEFAULT_MODEL") or str(defaults.get("default_model", "gpt-5.5")),
            timeout_seconds=_as_int(os.getenv("LUCIO_AGENT_TIMEOUT_SECONDS"), int(defaults.get("timeout_seconds", 120))),
            max_prompt_chars=_as_int(os.getenv("LUCIO_AGENT_MAX_PROMPT_CHARS"), int(defaults.get("max_prompt_chars", 200000))),
            max_output_chars=_as_int(os.getenv("LUCIO_AGENT_MAX_OUTPUT_CHARS"), int(defaults.get("max_output_chars", 65536))),
            use_memory_gateway=_as_bool(os.getenv("LUCIO_AGENT_USE_MEMORY_GATEWAY"), bool(defaults.get("use_memory_gateway", True))),
            use_delegation=_as_bool(os.getenv("LUCIO_AGENT_USE_DELEGATION"), bool(defaults.get("use_delegation", True))),
            default_execution_mode=os.getenv("LUCIO_AGENT_DEFAULT_EXECUTION_MODE") or str(defaults.get("default_execution_mode", "governed_autorun")),
            allow_direct_local_tools=_as_bool(os.getenv("LUCIO_AGENT_ALLOW_DIRECT_LOCAL_TOOLS"), bool(defaults.get("allow_direct_local_tools", False))),
            raw_default_visible=False,
            multimodal_enabled=lucio_enabled and _as_bool(os.getenv("LUCIO_MULTIMODAL_ENABLED"), bool(multimodal.get("enabled", False))),
            multimodal_provider=os.getenv("LUCIO_MULTIMODAL_PROVIDER") or ("disabled" if not lucio_enabled else str(multimodal.get("provider", "disabled"))),
            multimodal_allowed_content_types=[
                item.strip()
                for item in (allowed_content_types or ",".join(multimodal.get("allowed_content_types") or [])).split(",")
                if item.strip()
            ],
            multimodal_store_images=_as_bool(os.getenv("LUCIO_MULTIMODAL_STORE_IMAGES"), bool(multimodal.get("store_images", True))),
            multimodal_memory_write_default=_as_bool(os.getenv("LUCIO_MULTIMODAL_MEMORY_WRITE_DEFAULT"), bool(multimodal.get("memory_write_default", False))),
            multimodal_redaction_required=_as_bool(os.getenv("LUCIO_MULTIMODAL_REDACTION_REQUIRED"), bool(multimodal.get("redaction_required", True))),
            multimodal_delegation_enabled=_as_bool(os.getenv("LUCIO_MULTIMODAL_DELEGATION_ENABLED"), bool(multimodal.get("delegation_enabled", True))),
            visible_in_ux=lucio_enabled and _as_bool(os.getenv("LUCIO_VISIBLE_IN_UX"), bool(defaults.get("visible_in_ux", False))),
            allow_new_sessions=lucio_enabled and _as_bool(os.getenv("LUCIO_ALLOW_NEW_SESSIONS"), bool(defaults.get("allow_new_sessions", False))),
        )

    def status(
        self,
        *,
        last_error_sanitized: str | None = None,
        last_provider_error_at: str | None = None,
    ) -> LucioConfigStatus:
        runtime = self.runtime()
        provider_disabled = runtime.provider == "disabled"
        return LucioConfigStatus(
            enabled=runtime.enabled,
            api_key_configured=bool(runtime.api_key),
            provider=runtime.provider,
            provider_status="disabled_by_config" if provider_disabled else ("configured" if runtime.api_key else "missing_auth"),
            provider_required=False,
            provider_configured=bool(runtime.api_key) and not provider_disabled,
            auth_present=bool(runtime.api_key) and not provider_disabled,
            openai_enabled=runtime.openai_enabled,
            base_url_configured=bool(runtime.base_url),
            project_configured=bool(runtime.project),
            organization_configured=bool(runtime.organization),
            default_model=runtime.default_model,
            model_configured=bool(runtime.default_model),
            model_available_or_unknown="unknown",
            timeout_seconds=runtime.timeout_seconds,
            max_prompt_chars=runtime.max_prompt_chars,
            max_output_chars=runtime.max_output_chars,
            use_memory_gateway=runtime.use_memory_gateway,
            use_delegation=runtime.use_delegation,
            default_execution_mode=runtime.default_execution_mode,
            allow_direct_local_tools=runtime.allow_direct_local_tools,
            raw_default_visible=False,
            multimodal_enabled=runtime.multimodal_enabled,
            multimodal_provider=runtime.multimodal_provider,
            multimodal_allowed_content_types=runtime.multimodal_allowed_content_types,
            multimodal_store_images=runtime.multimodal_store_images,
            multimodal_memory_write_default=runtime.multimodal_memory_write_default,
            multimodal_redaction_required=runtime.multimodal_redaction_required,
            multimodal_delegation_enabled=runtime.multimodal_delegation_enabled,
            visible_in_ux=runtime.visible_in_ux,
            allow_new_sessions=runtime.allow_new_sessions,
            last_error_sanitized=last_error_sanitized,
            last_provider_error=last_error_sanitized,
            last_provider_error_at=last_provider_error_at,
        )
