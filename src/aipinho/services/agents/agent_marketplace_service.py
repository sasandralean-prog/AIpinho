from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.marketplace import (
    AgentHeartbeat,
    AgentHealthSnapshot,
    AgentManifest,
    AgentMarketplaceSnapshot,
    CapabilityMatch,
    CapabilityNegotiationResult,
    CapabilityQuery,
)
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


TRUST_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
HEALTH_RANK = {"online": 4, "degraded": 2, "offline": 1, "unhealthy": 0, "disabled": -1}


class AgentMarketplaceService:
    CONFIG_PATH = PATHS.config_root / "agents" / "agent_marketplace.yaml"

    def __init__(self) -> None:
        self.config = load_yaml_file(self.CONFIG_PATH, critical=True, root=PATHS.config_root)
        self.marketplace_config = self.config.get("marketplace", {}) if isinstance(self.config.get("marketplace"), dict) else {}
        self.runtime_path = self._runtime_path()

    def snapshot(self) -> AgentMarketplaceSnapshot:
        manifests = self.list_agents(include_disabled=True)
        health = [self.health_for(agent.agent_id) for agent in manifests]
        capabilities: dict[str, list[str]] = {}
        for agent in manifests:
            for capability in agent.capabilities:
                capabilities.setdefault(capability.capability_id, []).append(agent.agent_id)
        warnings = []
        if any(item.health_status in {"degraded", "unhealthy", "disabled"} for item in health):
            warnings.append("agent_health_not_all_online")
        return AgentMarketplaceSnapshot(
            status="degraded" if warnings else "ok",
            agents=manifests,
            health=health,
            capabilities={key: sorted(values) for key, values in sorted(capabilities.items())},
            warnings=warnings,
        )

    def status(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        return {
            "status": snapshot.status,
            "enabled": bool(self.marketplace_config.get("enabled", True)),
            "agent_count": len(snapshot.agents),
            "capability_count": len(snapshot.capabilities),
            "runtime_registry_path": str(self.runtime_path),
            "warnings": snapshot.warnings,
        }

    def list_agents(self, *, include_disabled: bool = False) -> list[AgentManifest]:
        agents = self._static_agents()
        runtime = self._read_runtime()
        dynamic = runtime.get("dynamic_agents", {}) if isinstance(runtime.get("dynamic_agents"), dict) else {}
        removed = set(runtime.get("removed_agents", []) or [])
        by_id = {agent.agent_id: agent for agent in agents if agent.agent_id not in removed}
        for value in dynamic.values():
            try:
                manifest = AgentManifest.model_validate(value)
            except Exception:
                continue
            if manifest.agent_id not in removed:
                by_id[manifest.agent_id] = manifest
        health = runtime.get("health", {}) if isinstance(runtime.get("health"), dict) else {}
        for agent_id, item in list(by_id.items()):
            state = health.get(agent_id) if isinstance(health.get(agent_id), dict) else {}
            if state.get("auto_disabled"):
                by_id[agent_id] = item.model_copy(update={"health_status": "disabled", "lifecycle_status": "disabled"})
            elif state.get("health_status"):
                by_id[agent_id] = item.model_copy(update={"health_status": state.get("health_status")})
        values = list(by_id.values())
        if not include_disabled:
            values = [agent for agent in values if agent.lifecycle_status != "disabled" and agent.health_status != "disabled"]
        return sorted(values, key=lambda item: (-item.priority, item.agent_id))

    def register_manifest(self, manifest: AgentManifest) -> AgentManifest:
        runtime = self._read_runtime()
        dynamic = runtime.setdefault("dynamic_agents", {})
        dynamic[manifest.agent_id] = manifest.model_dump(mode="json")
        removed = set(runtime.get("removed_agents", []) or [])
        removed.discard(manifest.agent_id)
        runtime["removed_agents"] = sorted(removed)
        self._write_runtime(runtime)
        return manifest

    def remove_agent(self, agent_id: str) -> dict[str, Any]:
        runtime = self._read_runtime()
        dynamic = runtime.setdefault("dynamic_agents", {})
        dynamic.pop(agent_id, None)
        removed = set(runtime.get("removed_agents", []) or [])
        removed.add(agent_id)
        runtime["removed_agents"] = sorted(removed)
        self._write_runtime(runtime)
        return {"status": "removed", "agent_id": agent_id}

    def disable_agent(self, agent_id: str, *, reason: str = "operator_disabled") -> AgentHealthSnapshot:
        runtime = self._read_runtime()
        health = runtime.setdefault("health", {})
        item = health.setdefault(agent_id, {})
        item.update(
            {
                "health_status": "disabled",
                "auto_disabled": True,
                "updated_at": utc_now(),
                "last_reason": reason,
            }
        )
        self._write_runtime(runtime)
        return self.health_for(agent_id)

    def heartbeat(self, heartbeat: AgentHeartbeat) -> AgentHealthSnapshot:
        runtime = self._read_runtime()
        health = runtime.setdefault("health", {})
        current = health.setdefault(heartbeat.agent_id, {})
        status = heartbeat.status if heartbeat.available else "offline"
        current.update(
            {
                "health_status": status,
                "last_heartbeat_at": heartbeat.created_at,
                "average_latency_ms": heartbeat.average_latency_ms,
                "queue_depth": heartbeat.queue_depth,
                "updated_at": utc_now(),
            }
        )
        if status == "online":
            current["consecutive_failures"] = 0
            current["auto_disabled"] = False
        if heartbeat.errors:
            current["total_failures"] = int(current.get("total_failures") or 0) + int(heartbeat.errors)
            current["consecutive_failures"] = int(current.get("consecutive_failures") or 0) + int(heartbeat.errors)
        self._maybe_auto_disable(current)
        self._write_runtime(runtime)
        return self.health_for(heartbeat.agent_id)

    def record_failure(self, agent_id: str, *, reason: str = "runtime_failure") -> AgentHealthSnapshot:
        runtime = self._read_runtime()
        health = runtime.setdefault("health", {})
        current = health.setdefault(agent_id, {})
        current["health_status"] = "degraded"
        current["consecutive_failures"] = int(current.get("consecutive_failures") or 0) + 1
        current["total_failures"] = int(current.get("total_failures") or 0) + 1
        current["last_reason"] = reason
        current["updated_at"] = utc_now()
        self._maybe_auto_disable(current)
        self._write_runtime(runtime)
        return self.health_for(agent_id)

    def health_for(self, agent_id: str) -> AgentHealthSnapshot:
        runtime = self._read_runtime()
        state = runtime.get("health", {}).get(agent_id, {}) if isinstance(runtime.get("health"), dict) else {}
        return AgentHealthSnapshot(
            agent_id=agent_id,
            health_status=state.get("health_status") or self._manifest_health(agent_id),
            last_heartbeat_at=state.get("last_heartbeat_at"),
            consecutive_failures=int(state.get("consecutive_failures") or 0),
            total_failures=int(state.get("total_failures") or 0),
            auto_disabled=bool(state.get("auto_disabled", False)),
            average_latency_ms=state.get("average_latency_ms"),
            queue_depth=state.get("queue_depth"),
            updated_at=state.get("updated_at") or utc_now(),
        )

    def query_capability(self, query: CapabilityQuery) -> CapabilityNegotiationResult:
        candidates = [self._match(agent, query.capability_id) for agent in self.list_agents(include_disabled=query.include_unhealthy)]
        candidates = [item for item in candidates if item is not None]
        if query.required_trust_level:
            minimum = TRUST_RANK.get(query.required_trust_level, 0)
            candidates = [item for item in candidates if TRUST_RANK.get(item.trust_level, 0) >= minimum]
        if not query.include_unhealthy:
            candidates = [item for item in candidates if item.health_status not in {"unhealthy", "disabled", "offline"}]
        candidates.sort(key=lambda item: item.score, reverse=True)
        return CapabilityNegotiationResult(
            query=query,
            selected=candidates[0] if candidates else None,
            candidates=candidates,
            status="matched" if candidates else "no_match",
            reason_code=None if candidates else "capability_not_available",
        )

    def select_agent_for_capability(self, capability_id: str) -> CapabilityMatch | None:
        return self.query_capability(CapabilityQuery(capability_id=capability_id)).selected

    def _match(self, agent: AgentManifest, capability_id: str) -> CapabilityMatch | None:
        if capability_id not in {capability.capability_id for capability in agent.capabilities}:
            return None
        health = self.health_for(agent.agent_id)
        health_score = HEALTH_RANK.get(health.health_status, 0)
        score = (
            health_score * int(self.marketplace_config.get("selection", {}).get("health_weight", 40))
            + TRUST_RANK.get(agent.trust_level, 0) * int(self.marketplace_config.get("selection", {}).get("trust_weight", 20))
            + agent.priority * int(self.marketplace_config.get("selection", {}).get("priority_weight", 20)) / 100
            - agent.cost * int(self.marketplace_config.get("selection", {}).get("cost_weight", 10))
            - min(agent.latency_ms, 5000) * int(self.marketplace_config.get("selection", {}).get("latency_weight", 10)) / 1000
        )
        reasons = [f"capability:{capability_id}", f"health:{health.health_status}", f"trust:{agent.trust_level}"]
        warnings = []
        if health.health_status != "online":
            warnings.append(f"health_status:{health.health_status}")
        return CapabilityMatch(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            capability_id=capability_id,
            trust_level=agent.trust_level,
            health_status=health.health_status,
            runtime_profile=agent.runtime_profile,
            score=round(float(score), 3),
            cost=agent.cost,
            latency_ms=agent.latency_ms,
            priority=agent.priority,
            reasons=reasons,
            warnings=warnings,
        )

    def _static_agents(self) -> list[AgentManifest]:
        values = self.config.get("agents", []) if isinstance(self.config.get("agents", []), list) else []
        agents: list[AgentManifest] = []
        for item in values:
            if isinstance(item, dict):
                agents.append(AgentManifest.model_validate(item))
        return agents

    def _manifest_health(self, agent_id: str) -> str:
        for agent in self._static_agents():
            if agent.agent_id == agent_id:
                return agent.health_status
        runtime = self._read_runtime()
        dynamic = runtime.get("dynamic_agents", {}) if isinstance(runtime.get("dynamic_agents"), dict) else {}
        item = dynamic.get(agent_id) if isinstance(dynamic.get(agent_id), dict) else None
        if item:
            return str(item.get("health_status") or "online")
        return "offline"

    def _maybe_auto_disable(self, state: dict[str, Any]) -> None:
        failures = int(state.get("consecutive_failures") or 0)
        threshold = int(self.marketplace_config.get("auto_disable_after_failures") or 3)
        if failures >= threshold:
            state["health_status"] = "disabled"
            state["auto_disabled"] = True

    def _runtime_path(self) -> Path:
        configured = str(self.marketplace_config.get("dynamic_registry_path") or "data/runtime/agent_marketplace_runtime.json")
        return resolve_within_root(PATHS.project_root / configured, PATHS.project_root)

    def _read_runtime(self) -> dict[str, Any]:
        if not self.runtime_path.exists():
            return {"dynamic_agents": {}, "removed_agents": [], "health": {}}
        try:
            loaded = json.loads(self.runtime_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"dynamic_agents": {}, "removed_agents": [], "health": {"__runtime__": {"health_status": "degraded"}}}
        return loaded if isinstance(loaded, dict) else {"dynamic_agents": {}, "removed_agents": [], "health": {}}

    def _write_runtime(self, data: dict[str, Any]) -> None:
        self.runtime_path.parent.mkdir(parents=True, exist_ok=True)
        self.runtime_path.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True), encoding="utf-8")
