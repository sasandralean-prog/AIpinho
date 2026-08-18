from types import SimpleNamespace

from aipinho.services.mobile_view_models import mobile_endpoint_inventory_service as inventory_module
from aipinho.services.mobile_view_models.mobile_endpoint_inventory_service import MobileEndpointInventoryService


def test_routes_yaml_is_valid_endpoint_inventory_source(tmp_path, monkeypatch):
    config_root = tmp_path / "config"
    routes_root = config_root / "routes"
    routes_root.mkdir(parents=True)
    (routes_root / "routes.yaml").write_text(
        """
routes:
  - path: /api/v1/health
  - path: /api/v1/mobile/view-model/dashboard
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        inventory_module,
        "PATHS",
        SimpleNamespace(project_root=tmp_path, config_root=config_root),
    )

    inventory = MobileEndpointInventoryService().inventory()

    assert inventory["status"] == "ok"
    assert inventory["total"] == 2
    assert inventory["source"].endswith("routes.yaml")
    assert inventory["warnings"]
