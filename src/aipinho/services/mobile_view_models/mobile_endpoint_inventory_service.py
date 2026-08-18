from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS


class MobileEndpointInventoryService:
    def inventory(self) -> dict[str, object]:
        grouped_json = PATHS.project_root / "endpoint_inventory_grouped.json"
        routes_yaml = PATHS.config_root / "routes" / "routes.yaml"
        warnings: list[str] = []
        if grouped_json.exists():
            data = json.loads(grouped_json.read_text(encoding="utf-8"))
            total = int(data.get("total", data.get("endpoint_inventory_total", 0)))
            return {"status": "ok", "source": str(grouped_json), "total": total, "warnings": warnings}
        if routes_yaml.exists():
            lines = routes_yaml.read_text(encoding="utf-8").splitlines()
            route_lines = [line for line in lines if "/api/v1/" in line]
            warnings.append("endpoint_inventory_grouped not found; using canonical config/routes/routes.yaml")
            return {"status": "ok", "source": str(routes_yaml), "total": len(route_lines), "warnings": warnings}
        warnings.append("endpoint inventory unavailable")
        return {"status": "degraded", "source": "unavailable", "total": 0, "warnings": warnings}
