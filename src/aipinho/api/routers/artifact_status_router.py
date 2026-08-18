from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from starlette.responses import FileResponse, Response

from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactDownloadService
from aipinho.services.artifacts.artifact_link_policy_service import ArtifactLinkPolicyService
from aipinho.services.artifacts.artifact_manifest_service import ArtifactManifestService
from aipinho.services.security.local_token_service import LocalTokenService

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifact-service-base"])


@router.get("/links/policy")
def artifact_links_policy() -> dict[str, object]:
    return ArtifactLinkPolicyService().policy()


@router.get("/{artifact_id}/metadata")
def artifact_metadata(artifact_id: str) -> dict[str, object]:
    return ArtifactManifestService().metadata(artifact_id)


@router.get("/{artifact_id}/manifest")
def artifact_manifest(artifact_id: str) -> dict[str, object]:
    return ArtifactManifestService().metadata(artifact_id)


@router.get("/{artifact_id}/download")
def artifact_download(artifact_id: str, authorization: str | None = Header(default=None)):
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")
    try:
        path = ArtifactDownloadService().path(artifact_id)
        return FileResponse(path, filename=path.name)
    except FileNotFoundError as exc:
        try:
            artifact, content = AgentToolGatewayService().read_artifact_bytes(artifact_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="artifact_not_found") from exc
        if artifact.status != "ready":
            raise HTTPException(status_code=409, detail="artifact_not_ready")
        return Response(
            content,
            media_type=artifact.content_type,
            headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/zip/{artifact_id}/download")
def artifact_zip_download(artifact_id: str, authorization: str | None = Header(default=None)):
    return artifact_download(artifact_id, authorization)
