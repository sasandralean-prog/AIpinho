from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.agents.marketplace import AgentHeartbeat, AgentManifest, CapabilityQuery
from aipinho.services.agents.agent_marketplace_service import AgentMarketplaceService

router = APIRouter(prefix="/api/v1/agent-marketplace", tags=["agent-marketplace"])


@router.get("/status")
def agent_marketplace_status() -> dict[str, object]:
    return AgentMarketplaceService().status()


@router.get("/agents")
def list_agents(include_disabled: bool = False) -> dict[str, object]:
    service = AgentMarketplaceService()
    return {
        "status": "ok",
        "agents": [agent.model_dump(mode="json") for agent in service.list_agents(include_disabled=include_disabled)],
    }


@router.get("/health")
def marketplace_health() -> dict[str, object]:
    snapshot = AgentMarketplaceService().snapshot()
    return {
        "status": snapshot.status,
        "health": [item.model_dump(mode="json") for item in snapshot.health],
        "warnings": snapshot.warnings,
    }


@router.get("/snapshot")
def marketplace_snapshot() -> dict[str, object]:
    return AgentMarketplaceService().snapshot().model_dump(mode="json")


@router.post("/agents")
def register_agent(manifest: AgentManifest) -> dict[str, object]:
    agent = AgentMarketplaceService().register_manifest(manifest)
    return {"status": "registered", "agent": agent.model_dump(mode="json")}


@router.delete("/agents/{agent_id}")
def remove_agent(agent_id: str) -> dict[str, object]:
    return AgentMarketplaceService().remove_agent(agent_id)


@router.post("/agents/{agent_id}/disable")
def disable_agent(agent_id: str, reason: str = "operator_disabled") -> dict[str, object]:
    return AgentMarketplaceService().disable_agent(agent_id, reason=reason).model_dump(mode="json")


@router.post("/agents/{agent_id}/heartbeat")
def agent_heartbeat(agent_id: str, heartbeat: AgentHeartbeat) -> dict[str, object]:
    payload = heartbeat.model_copy(update={"agent_id": agent_id})
    return AgentMarketplaceService().heartbeat(payload).model_dump(mode="json")


@router.post("/agents/{agent_id}/failure")
def record_agent_failure(agent_id: str, reason: str = "runtime_failure") -> dict[str, object]:
    return AgentMarketplaceService().record_failure(agent_id, reason=reason).model_dump(mode="json")


@router.get("/capabilities/{capability_id}")
def query_capability_get(capability_id: str, include_unhealthy: bool = False) -> dict[str, object]:
    query = CapabilityQuery(capability_id=capability_id, include_unhealthy=include_unhealthy)
    return AgentMarketplaceService().query_capability(query).model_dump(mode="json")


@router.post("/query")
def query_capability(query: CapabilityQuery) -> dict[str, object]:
    return AgentMarketplaceService().query_capability(query).model_dump(mode="json")
