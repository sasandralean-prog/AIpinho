from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.agents.marketplace import (
    AgentCapabilityDescriptor,
    AgentHeartbeat,
    AgentManifest,
    CapabilityQuery,
)
from aipinho.services.agents.agent_marketplace_service import AgentMarketplaceService
from aipinho.services.runtime.intelligent_planner_service import IntelligentPlannerService


def _agent(agent_id: str, capability: str, *, priority: int = 50, latency_ms: int = 100) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        name=agent_id,
        capabilities=[AgentCapabilityDescriptor(capability_id=capability)],
        priority=priority,
        latency_ms=latency_ms,
        trust_level="L3",
    )


def test_dynamic_registration_and_removal_roundtrip() -> None:
    service = AgentMarketplaceService()
    agent_id = f"dynamic_agent_{uuid4().hex}"
    capability = f"capability_{uuid4().hex}"

    try:
        service.register_manifest(_agent(agent_id, capability))
        result = service.query_capability(CapabilityQuery(capability_id=capability))

        assert result.status == "matched"
        assert result.selected is not None
        assert result.selected.agent_id == agent_id

        service.remove_agent(agent_id)
        removed = service.query_capability(CapabilityQuery(capability_id=capability))

        assert removed.status == "no_match"
    finally:
        service.remove_agent(agent_id)


def test_heartbeat_updates_health_snapshot() -> None:
    service = AgentMarketplaceService()
    agent_id = f"heartbeat_agent_{uuid4().hex}"
    capability = f"heartbeat_capability_{uuid4().hex}"
    service.register_manifest(_agent(agent_id, capability))

    health = service.heartbeat(
        AgentHeartbeat(
            agent_id=agent_id,
            status="online",
            average_latency_ms=42,
            queue_depth=2,
        )
    )

    assert health.health_status == "online"
    assert health.average_latency_ms == 42
    assert health.queue_depth == 2
    service.remove_agent(agent_id)


def test_health_degradation_auto_disables_and_failover_selects_healthy_agent() -> None:
    service = AgentMarketplaceService()
    capability = f"failover_capability_{uuid4().hex}"
    first = f"failover_primary_{uuid4().hex}"
    second = f"failover_secondary_{uuid4().hex}"
    try:
        service.register_manifest(_agent(first, capability, priority=90, latency_ms=50))
        service.register_manifest(_agent(second, capability, priority=70, latency_ms=80))

        assert service.query_capability(CapabilityQuery(capability_id=capability)).selected.agent_id == first  # type: ignore[union-attr]

        service.record_failure(first)
        service.record_failure(first)
        health = service.record_failure(first)
        result = service.query_capability(CapabilityQuery(capability_id=capability))

        assert health.auto_disabled is True
        assert result.selected is not None
        assert result.selected.agent_id == second
    finally:
        service.remove_agent(first)
        service.remove_agent(second)


def test_capability_marketplace_returns_parallel_candidates() -> None:
    service = AgentMarketplaceService()
    capability = f"parallel_capability_{uuid4().hex}"
    first = f"parallel_a_{uuid4().hex}"
    second = f"parallel_b_{uuid4().hex}"
    try:
        service.register_manifest(_agent(first, capability, priority=60))
        service.register_manifest(_agent(second, capability, priority=61))

        result = service.query_capability(CapabilityQuery(capability_id=capability))
        ids = {item.agent_id for item in result.candidates}

        assert {first, second}.issubset(ids)
        assert result.selected is not None
    finally:
        service.remove_agent(first)
        service.remove_agent(second)


def test_intelligent_planner_selects_agents_from_marketplace_not_worker_names() -> None:
    report = IntelligentPlannerService().plan(objective="Analise este projeto Android com OCR e UI.")
    executors = {node.executor for node in report.nodes}

    assert {"planner_local", "executor_local", "debugger_local", "vision_local", "ocr_local", "review_local"}.issubset(executors)
    assert "PlannerWorker" not in executors
    assert "ExecutorWorker" not in executors
    assert "VisionWorker" not in executors


def test_marketplace_sources_do_not_branch_by_provider() -> None:
    source = AgentMarketplaceService.__module__
    import inspect
    import aipinho.services.agents.agent_marketplace_service as marketplace_module

    text = inspect.getsource(marketplace_module)
    assert "if gemini" not in text.lower()
    assert "if codex" not in text.lower()
    assert source.endswith("agent_marketplace_service")
