from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

Transport = Callable[[str, str, dict[str, str], bytes | None, float], tuple[int, Any]]


@dataclass(frozen=True)
class ApiResult:
    ok: bool
    status_code: int
    data: Any
    error: str | None = None


class BaseClient:
    def __init__(self, base_url: str, token: str | None = None, timeout: float = 5.0, transport: Transport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.transport = transport

    def with_token(self, token: str | None) -> "BaseClient":
        return self.__class__(self.base_url, token=token, timeout=self.timeout, transport=self.transport)

    def headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def redact(self, text: str) -> str:
        if self.token:
            text = text.replace(self.token, "[REDACTED_TOKEN]")
        return text.replace("Authorization: Bearer", "Authorization: Bearer [REDACTED_TOKEN]")

    def request(self, method: str, path: str, payload: Any | None = None) -> ApiResult:
        url = f"{self.base_url}{path}"
        body = None if payload is None else json.dumps(payload, ensure_ascii=True).encode("utf-8")
        try:
            if self.transport is not None:
                status_code, data = self.transport(method, url, self.headers(), body, self.timeout)
                return ApiResult(ok=200 <= status_code < 300, status_code=status_code, data=data, error=None if status_code < 400 else str(data))
            request = urllib.request.Request(url, data=body, headers=self.headers(), method=method)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - local configured backend client
                content = response.read()
                if not content:
                    data = {}
                else:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type or content.lstrip().startswith((b"{", b"[")):
                        data = json.loads(content.decode("utf-8"))
                    else:
                        data = content
                return ApiResult(ok=True, status_code=response.status, data=data)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"detail": self.redact(raw)}
            return ApiResult(ok=False, status_code=exc.code, data=data, error=self.redact(str(data)))
        except Exception as exc:  # pragma: no cover - exercised through UI degraded mode
            return ApiResult(ok=False, status_code=0, data={}, error=self.redact(str(exc)))

    def get(self, path: str) -> ApiResult:
        return self.request("GET", path)

    def post(self, path: str, payload: Any | None = None) -> ApiResult:
        return self.request("POST", path, payload)

    def patch(self, path: str, payload: Any | None = None) -> ApiResult:
        return self.request("PATCH", path, payload)

    def delete(self, path: str) -> ApiResult:
        return self.request("DELETE", path)
