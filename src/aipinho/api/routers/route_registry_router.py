from __future__ import annotations

from fastapi import APIRouter, Request

from aipinho.registries.route_registry import RouteRegistry

router = APIRouter(prefix="/api/v1", tags=["routes"])


@router.get("/routes")
def list_routes(request: Request) -> dict[str, object]:
    routes = RouteRegistry().list_routes(request.app)
    return {"status": "ok", "routes": routes}
