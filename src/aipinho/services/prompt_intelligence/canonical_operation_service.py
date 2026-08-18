from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class CanonicalOperationService:
    """Maps semantic intent and router output to one operation vocabulary."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "chat" / "canonical_operation_map.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def from_intent(self, intent_map: Any) -> str:
        semantic_graph = getattr(intent_map, "semantic_intent_graph", None)
        if semantic_graph is not None:
            state_effect = str(getattr(semantic_graph, "state_effect", "none"))
            readonly_contract = bool(getattr(semantic_graph, "readonly_contract", False))
            if readonly_contract or state_effect in {"knowledge_only", "planning_only", "build_execution", "runtime_execution"}:
                intent_type = str(getattr(intent_map, "intent_type", "unknown"))
                return str((self.config.get("intent_types", {}) or {}).get(intent_type, "unknown"))
        action = self._action_operation(getattr(intent_map, "requested_actions", []))
        if action:
            return action
        intent_type = str(getattr(intent_map, "intent_type", "unknown"))
        return str((self.config.get("intent_types", {}) or {}).get(intent_type, "unknown"))

    def from_router(self, operation_type: str, metadata: dict[str, Any] | None = None) -> str:
        mapped_router = (self.config.get("router_aliases", {}) or {}).get(operation_type)
        if mapped_router:
            return str(mapped_router)
        action = self._action_operation((metadata or {}).get("requested_actions", []))
        if action:
            return action
        return operation_type

    def _action_operation(self, actions: Any) -> str | None:
        precedence = self.config.get("action_precedence", {}) or {}
        for action in actions or []:
            mapped = precedence.get(str(action))
            if mapped:
                return str(mapped)
        return None

    def status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "canonical_operation",
            "intent_types": len(self.config.get("intent_types", {}) or {}),
            "router_aliases": len(self.config.get("router_aliases", {}) or {}),
        }
