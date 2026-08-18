from __future__ import annotations

from fastapi import FastAPI


class RouteRegistry:
    def list_routes(self, app: FastAPI) -> list[dict[str, object]]:
        routes: list[dict[str, object]] = []
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = sorted(getattr(route, "methods", []) or [])
            name = getattr(route, "name", None)
            if path is None or not path.startswith("/api/v1"):
                continue
            routes.append({"path": path, "methods": methods, "name": name})
        return sorted(routes, key=lambda item: (str(item["path"]), str(item["methods"])))

    def status(self, app: FastAPI) -> dict[str, object]:
        routes = self.list_routes(app)
        return {"status": "ok", "routes": len(routes)}
