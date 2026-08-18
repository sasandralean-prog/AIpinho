__all__ = ["CodexAgentService"]


def __getattr__(name: str):
    if name == "CodexAgentService":
        from aipinho.services.codex_agent.codex_agent_service import CodexAgentService

        return CodexAgentService
    raise AttributeError(name)
