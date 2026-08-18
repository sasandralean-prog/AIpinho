from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.mobile_view_models.mobile_view_model_service import MobileViewModelService
from aipinho.services.agents.agent_marketplace_service import AgentMarketplaceService
from aipinho.services.projects.project_profile_registry_service import ProjectProfileRegistryService
from aipinho.services.sandbox.sandbox_view_model_service import SandboxViewModelService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService

router = APIRouter(prefix="/api/v1/mobile/view-model", tags=["mobile-view-model"])


def _dump(model) -> dict[str, object]:
    return model.model_dump(by_alias=True)


@router.get("/status")
def mobile_view_model_status() -> dict[str, object]:
    return MobileViewModelService().status()


@router.get("/dashboard")
def mobile_dashboard_view_model() -> dict[str, object]:
    return _dump(MobileViewModelService().dashboard())


@router.get("/projects")
def mobile_project_profiles_view_model() -> dict[str, object]:
    return ProjectProfileRegistryService().mobile_selector_view()


@router.get("/skills")
def mobile_skills_view_model() -> dict[str, object]:
    return SkillManifestRegistryService().mobile_view()


@router.get("/agents")
def mobile_agent_marketplace_view_model() -> dict[str, object]:
    snapshot = AgentMarketplaceService().snapshot()
    return {
        "status": snapshot.status,
        "title": "Agent Marketplace",
        "human_summary": f"{len(snapshot.agents)} agentes registrados e {len(snapshot.capabilities)} capabilities descobertas.",
        "agents": [agent.model_dump(mode="json") for agent in snapshot.agents],
        "health": [item.model_dump(mode="json") for item in snapshot.health],
        "capabilities": snapshot.capabilities,
        "warnings": snapshot.warnings,
        "source": "/api/v1/agent-marketplace/snapshot",
    }


@router.get("/sandbox")
def mobile_sandbox_view_model() -> dict[str, object]:
    return SandboxViewModelService().view_model()


@router.get("/chat/{session_id}")
def mobile_chat_view_model(session_id: str) -> dict[str, object]:
    return _dump(MobileViewModelService().chat(session_id))


@router.get("/pipeline")
def mobile_pipeline_view_model() -> dict[str, object]:
    return _dump(MobileViewModelService().pipeline())


@router.get("/pipeline/{task_id}")
def mobile_pipeline_task_view_model(task_id: str) -> dict[str, object]:
    return _dump(MobileViewModelService().pipeline(task_id))


@router.get("/debugger")
def mobile_debugger_view_model() -> dict[str, object]:
    return _dump(MobileViewModelService().debugger())


@router.get("/debugger/trace/{trace_id}")
def mobile_debugger_trace_view_model(trace_id: str) -> dict[str, object]:
    return _dump(MobileViewModelService().debugger_trace(trace_id))


@router.get("/config")
def mobile_config_view_model() -> dict[str, object]:
    return _dump(MobileViewModelService().config())


@router.get("/evidence/{evidence_type}/{ref_id}")
def mobile_evidence_view_model(evidence_type: str, ref_id: str) -> dict[str, object]:
    return _dump(MobileViewModelService().evidence(evidence_type, ref_id))


@router.get("/support-bundle/preview")
def mobile_support_bundle_preview() -> dict[str, object]:
    return _dump(MobileViewModelService().support_bundle_preview())


@router.post("/cards/{card_id}/copy")
def mobile_card_copy(card_id: str) -> dict[str, object]:
    try:
        return MobileViewModelService().copy_card(card_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="card_not_found") from exc


@router.post("/raw/{raw_ref}/copy")
def mobile_raw_copy(raw_ref: str) -> dict[str, object]:
    return MobileViewModelService().copy_raw(raw_ref)


@router.post("/refresh")
def mobile_view_model_refresh() -> dict[str, object]:
    return MobileViewModelService().refresh()
