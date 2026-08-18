from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService

router = APIRouter(prefix="/api/v1/dashboard", tags=["multi-agent-dashboard"])


def _service() -> MultiAgentObservabilityService:
    return MultiAgentObservabilityService()


@router.get("/multi-agent")
def multi_agent_dashboard() -> dict[str, object]:
    return _service().dashboard().model_dump()


@router.get("/health")
def multi_agent_dashboard_health() -> dict[str, object]:
    return _service().health()


@router.get("/state-consistency")
def multi_agent_state_consistency() -> dict[str, object]:
    return _service().state_consistency().model_dump()
