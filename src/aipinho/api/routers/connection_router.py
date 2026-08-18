from __future__ import annotations
from fastapi import APIRouter, HTTPException
from aipinho.schemas.supervisor.contracts import ConnectionTestRequest
from aipinho.services.supervisor.supervisor_core import ADBReverseService, ConnectionProfileService, ConnectionSuggestionService, ConnectionTestService
router = APIRouter(prefix="/api/v1/connection", tags=["connection"])
@router.get("/profiles")
def get_profiles() -> dict[str, object]:
    svc = ConnectionProfileService()
    return {"status": "ok", "selected_profile": svc.selected(), "profiles": [p.model_dump() for p in svc.list_profiles()]}
@router.post("/profiles/select")
def select_profile(payload: dict[str, object]) -> dict[str, object]:
    try:
        profile = ConnectionProfileService().select(str(payload.get("profile_id") or ""))
        return {"status": "ok", "profile": profile.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
@router.post("/test")
def test_connection(request: ConnectionTestRequest) -> dict[str, object]:
    result = ConnectionTestService().test(request)
    return {"status": result.status, "result": result.model_dump()}
@router.get("/adb/reverse-commands")
def adb_reverse_commands() -> dict[str, object]:
    status = ADBReverseService().commands()
    return {"status": "ok", "adb_reverse": status.model_dump()}

@router.get("/suggestions")
def connection_suggestions() -> dict[str, object]:
    return ConnectionSuggestionService().suggestions()
