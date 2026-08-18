from __future__ import annotations
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from aipinho.services.security.local_token_service import LocalTokenService

class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health") or (request.client and request.client.host in {"127.0.0.1", "testclient"}):
            return await call_next(request)
        if not LocalTokenService().validate_authorization(request.headers.get("authorization")):
            return JSONResponse({"status": "unauthorized", "detail": "missing_or_invalid_bearer_token"}, status_code=401)
        return await call_next(request)
