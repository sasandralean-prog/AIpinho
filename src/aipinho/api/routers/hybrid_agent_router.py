from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.agents.hybrid_execution import CodexDelegationRequest, CodexDiagnosticRequest, CodexModeSelectRequest, IslandChatRequest
from aipinho.services.agents.codex_hybrid_service import CodexHybridService
from aipinho.services.agents.interpretation_agent_service import InterpretationAgentService
from aipinho.services.lucio_agent import LucioAgentService


router = APIRouter(prefix="/api/v1", tags=["hybrid-agents"])


@router.post("/codex/mode-select")
def codex_mode_select(request: CodexModeSelectRequest) -> dict[str, object]:
    return {"status": "ok", "decision": CodexHybridService().select_mode(request).model_dump()}


@router.post("/codex/delegate-to-aipinho")
def codex_delegate(request: CodexDelegationRequest) -> dict[str, object]:
    try:
        return CodexHybridService().delegate_to_aipinho(request)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/codex/delegations/{delegation_id}")
def codex_delegation(delegation_id: str) -> dict[str, object]:
    try:
        return CodexHybridService().delegation_details(delegation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="delegation_not_found") from exc


@router.post("/codex/hybrid/collect-diagnostics")
def codex_collect_diagnostics(request: CodexDiagnosticRequest) -> dict[str, object]:
    try:
        return CodexHybridService().collect_diagnostics(request)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/agents/lucio/chat")
def lucio_chat(request: IslandChatRequest) -> dict[str, object]:
    service = LucioAgentService()
    if not service.config_service.runtime().enabled:
        return service.disabled_payload(session_id=request.session_id)
    try:
        return {"status": "ok", "response": InterpretationAgentService().chat("lucio", request).model_dump()}
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/agents/gemini/chat")
def gemini_chat(request: IslandChatRequest) -> dict[str, object]:
    try:
        return {"status": "ok", "response": InterpretationAgentService().chat("gemini", request).model_dump()}
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
