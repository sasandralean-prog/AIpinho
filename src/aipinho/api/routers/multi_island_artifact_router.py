from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.artifacts.artifact_generation import ArtifactRequest
from aipinho.services.artifacts.artifact_generator_service import ArtifactGeneratorService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService

router = APIRouter(prefix="/api/v1/agents", tags=["multi-island-artifacts"])


@router.post("/{agent_id}/artifacts")
def generate_agent_artifact(agent_id: str, request: ArtifactRequest) -> dict[str, object]:
    if request.source_agent != agent_id:
        request = request.model_copy(update={"source_agent": agent_id})
    result = ArtifactGeneratorService().generate(request)
    status = "ok" if result.status in {"READY", "READY_WITH_WARNINGS"} else "blocked"
    return {"status": status, "result": result.model_dump(), "raw_default_visible": False}


@router.get("/{agent_id}/artifacts")
def list_agent_artifacts(agent_id: str, session_id: str | None = None, limit: int = 200) -> dict[str, object]:
    return {
        "status": "ok",
        "agent_id": agent_id,
        "session_id": session_id,
        "artifacts": ArtifactRuntimeService().by_agent(agent_id, session_id=session_id, limit=limit),
        "source": "artifact_runtime",
        "raw_default_visible": False,
    }
