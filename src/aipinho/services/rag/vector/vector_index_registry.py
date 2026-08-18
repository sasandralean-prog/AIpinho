from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.vector.contracts import VectorNamespace
from aipinho.services.rag.vector.config import rag_config


class VectorIndexRegistry:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or rag_config("vector_index_registry.yaml")

    def list_namespaces(self, *, include_disabled: bool = True) -> list[VectorNamespace]:
        indexes = self.config.get("indexes", {}) if isinstance(self.config.get("indexes", {}), dict) else {}
        namespaces = []
        for namespace_id, data in indexes.items():
            if not isinstance(data, dict):
                continue
            if not include_disabled and not data.get("enabled", True):
                continue
            namespaces.append(VectorNamespace(namespace_id=str(namespace_id), **data))
        return namespaces

    def get_namespace(self, namespace_id: str) -> VectorNamespace | None:
        for namespace in self.list_namespaces(include_disabled=True):
            if namespace.namespace_id == namespace_id:
                return namespace
        return None

    def role_namespace(self, role_id: str) -> VectorNamespace | None:
        for namespace in self.list_namespaces(include_disabled=False):
            if namespace.namespace_type == "role" and namespace.role_id == role_id:
                return namespace
        return None

    def blocked_legacy_paths(self) -> list[str]:
        blocked = self.config.get("blocked_indexes", {}) if isinstance(self.config.get("blocked_indexes", {}), dict) else {}
        legacy = blocked.get("legacy_vectorstore", {}) if isinstance(blocked.get("legacy_vectorstore", {}), dict) else {}
        return [str(item) for item in legacy.get("paths", []) or []]

    def is_legacy_path(self, path: str | Path) -> bool:
        normalized = str(path).replace("\\", "/").lower()
        governed_abs = str(self.governed_root().resolve()).replace("\\", "/").lower()
        governed_rel = "data/vectorstores/governed"
        if normalized.startswith(governed_abs) or normalized.startswith(governed_rel):
            return False
        parts = [part for part in normalized.split("/") if part]
        for item in self.blocked_legacy_paths():
            pattern = item.replace("\\", "/").lower().strip("/")
            if not pattern:
                continue
            if "/" in pattern and pattern in normalized:
                return True
            if "/" not in pattern and pattern in parts:
                return True
        return False

    def governed_root(self) -> Path:
        return PATHS.project_root / "data" / "vectorstores" / "governed"

    def status(self) -> dict[str, object]:
        namespaces = self.list_namespaces(include_disabled=True)
        return {
            "status": "ok",
            "service": "vector_index_registry",
            "namespaces": len(namespaces),
            "enabled_namespaces": len([item for item in namespaces if item.enabled]),
            "disabled_namespaces": len([item for item in namespaces if not item.enabled]),
        }
