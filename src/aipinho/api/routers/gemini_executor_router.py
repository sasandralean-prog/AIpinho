from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.gemini_executor import GeminiExecutorRequest
from aipinho.services.gemini_executor import GeminiExecutorService

router = APIRouter(prefix="/api/v1/gemini-executor", tags=["gemini-executor"])


class CreateGeminiSessionRequest(AIpinhoModel):
    title: str = "Gemini Executor"


class RenameGeminiSessionRequest(AIpinhoModel):
    title: str


class GeminiApprovalRequest(AIpinhoModel):
    operation_id: str | None = None


@router.get("/health")
def health() -> dict[str, object]:
    return GeminiExecutorService().health()


@router.get("/config/status")
def config_status() -> dict[str, object]:
    return {"status": "ok", "config": GeminiExecutorService().config_service.status().model_dump()}


@router.post("/sessions")
def create_session(request: CreateGeminiSessionRequest | None = None) -> dict[str, object]:
    session = GeminiExecutorService().create_session(title=request.title if request else "Gemini Executor")
    return {"status": "ok", "session": session.model_dump()}


@router.get("/sessions")
def list_sessions() -> dict[str, object]:
    sessions = GeminiExecutorService().sessions()
    return {"status": "ok", "sessions": [session.model_dump() for session in sessions], "total": len(sessions)}


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, object]:
    session = GeminiExecutorService().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="gemini_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.post("/sessions/{session_id}/rename")
def rename_session(session_id: str, request: RenameGeminiSessionRequest) -> dict[str, object]:
    session = GeminiExecutorService().rename_session(session_id, request.title)
    if session is None:
        raise HTTPException(status_code=404, detail="gemini_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, object]:
    deleted = GeminiExecutorService().delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="gemini_session_not_found")
    return {"status": "ok", "deleted": True, "session_id": session_id}


@router.get("/sessions/{session_id}/messages")
def messages(session_id: str) -> dict[str, object]:
    try:
        messages = GeminiExecutorService().messages(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc
    return {"status": "ok", "messages": [message.model_dump() for message in messages]}


@router.get("/sessions/{session_id}/view-model")
def view_model(
    session_id: str,
    after_event_id: str | None = None,
) -> dict[str, object]:
    try:
        return GeminiExecutorService().mobile_view_model(session_id, after_event_id=after_event_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc


@router.get("/runs/{run_id}/events")
def run_events(
    run_id: str,
    after_event_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    service = GeminiExecutorService()
    if service.agent_kernel.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="gemini_run_not_found")
    return {
        "status": "ok",
        "run_id": run_id,
        "events": service.events(run_id, after_event_id=after_event_id, limit=limit),
    }


@router.post("/sessions/{session_id}/send")
def send(session_id: str, request: GeminiExecutorRequest) -> dict[str, object]:
    try:
        response = GeminiExecutorService().send(request.model_copy(update={"session_id": session_id}))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc
    return {"status": "ok", "response": response.model_dump()}


@router.post("/sessions/{session_id}/plan")
def plan(session_id: str, request: GeminiExecutorRequest) -> dict[str, object]:
    planned = request.model_copy(update={"session_id": session_id, "operation_type": "gemini_coding_plan"})
    try:
        response = GeminiExecutorService().send(planned)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc
    return {"status": "ok", "response": response.model_dump()}


@router.post("/sessions/{session_id}/preview")
def preview(session_id: str, request: GeminiExecutorRequest) -> dict[str, object]:
    try:
        response = GeminiExecutorService().preview(request.model_copy(update={"session_id": session_id}))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc
    return {"status": "ok", "response": response.model_dump()}


@router.post("/sessions/{session_id}/request-approval")
def request_approval(session_id: str, request: GeminiApprovalRequest | None = None) -> dict[str, object]:
    try:
        return GeminiExecutorService().request_approval(session_id, operation_id=request.operation_id if request else None)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc


@router.post("/sessions/{session_id}/apply-approved")
def apply_approved(session_id: str) -> dict[str, object]:
    try:
        return GeminiExecutorService().guarded_not_implemented(session_id, "apply_approved_patch")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc


@router.post("/sessions/{session_id}/run-approved-shell")
def run_approved_shell(session_id: str) -> dict[str, object]:
    try:
        return GeminiExecutorService().guarded_not_implemented(session_id, "run_approved_shell")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc


@router.get("/sessions/{session_id}/artifacts")
def artifacts(session_id: str) -> dict[str, object]:
    try:
        GeminiExecutorService().messages(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="gemini_session_not_found") from exc
    return {"status": "ok", "session_id": session_id, "artifacts": []}
