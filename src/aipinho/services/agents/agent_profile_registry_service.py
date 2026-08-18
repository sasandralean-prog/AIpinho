from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentProfile, AgentRegistryStatus
from aipinho.utils.yaml_loader import load_yaml_file


class AgentProfileRegistryService:
    def __init__(self, path: Path | None = None, *, root: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "agents" / "agent_registry.yaml"
        self.root = root or PATHS.config_root

    def _raw_agents(self) -> list[dict[str, Any]]:
        data = load_yaml_file(self.path, critical=True, root=self.root)
        agents = data.get("agents", [])
        if not isinstance(agents, list):
            raise ValueError("agent_registry_agents_must_be_list")
        return [item for item in agents if isinstance(item, dict)]

    def list_profiles(self, *, enabled: bool | None = None) -> list[AgentProfile]:
        profiles = [self._apply_runtime_overrides(AgentProfile(**item)) for item in self._raw_agents()]
        seen: set[str] = set()
        duplicate_ids: set[str] = set()
        for profile in profiles:
            if profile.agent_id in seen:
                duplicate_ids.add(profile.agent_id)
            seen.add(profile.agent_id)
        if duplicate_ids:
            raise ValueError(f"duplicate_agent_ids:{','.join(sorted(duplicate_ids))}")
        if enabled is not None:
            profiles = [profile for profile in profiles if profile.enabled is enabled]
        return profiles

    def _apply_runtime_overrides(self, profile: AgentProfile) -> AgentProfile:
        normalized = "".join(ch if ch.isalnum() else "_" for ch in profile.agent_id.upper())
        for name in (
            f"AIPINHO_AGENT_{normalized}_ENABLED",
            f"{normalized}_ENABLED",
            f"{normalized}_AGENT_ENABLED",
        ):
            value = os.getenv(name)
            if value is not None and value.strip():
                enabled = value.strip().lower() in {"1", "true", "yes", "on"}
                return profile.model_copy(update={"enabled": enabled})
        return profile

    def get(self, agent_id: str) -> AgentProfile | None:
        return next((profile for profile in self.list_profiles() if profile.agent_id == agent_id), None)

    def require(self, agent_id: str) -> AgentProfile:
        profile = self.get(agent_id)
        if profile is None:
            raise KeyError(agent_id)
        return profile

    def status(self) -> AgentRegistryStatus:
        profiles = self.list_profiles()
        enabled = [profile for profile in profiles if profile.enabled]
        disabled = [profile for profile in profiles if not profile.enabled]
        return AgentRegistryStatus(
            status="ok" if profiles else "degraded",
            profiles_loaded=len(profiles),
            enabled_profiles=len(enabled),
            disabled_profiles=len(disabled),
            agent_ids=[profile.agent_id for profile in profiles],
        )
