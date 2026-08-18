from __future__ import annotations

from apps.launcher.ui.api.agent_api_client import AgentEndpointConfig


AGENT_ENDPOINTS: tuple[AgentEndpointConfig, ...] = (
    AgentEndpointConfig(
        agent_id="codex_agent",
        display_name="Codex",
        route_prefix="/api/v1/codex-agent",
        operation_type="codex_chat",
        provider_label="Executor",
        external_provider_notice="Executor tecnico local governado por policy, approvals e validation.",
    ),
    AgentEndpointConfig(
        agent_id="gemini_executor",
        display_name="Gemini",
        route_prefix="/api/v1/gemini-executor",
        operation_type="gemini_chat",
        provider_label="Cloud Executor",
        external_provider_notice="Provider cloud externo. Secrets permanecem somente no backend local.",
    ),
)


def agent_endpoint(agent_id: str) -> AgentEndpointConfig:
    for config in AGENT_ENDPOINTS:
        if config.agent_id == agent_id:
            return config
    raise KeyError(f"unknown_agent_endpoint:{agent_id}")
