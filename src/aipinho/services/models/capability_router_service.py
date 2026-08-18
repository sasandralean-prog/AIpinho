from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.utils.yaml_loader import load_yaml_file


CORE_CAPABILITIES = [
    "text_chat",
    "code_assist",
    "planning",
    "intent_classification",
    "policy_reasoning",
    "embeddings",
    "reranker",
    "ocr",
    "vision",
    "workspace_search",
    "file_summarization",
    "patch_planning",
    "shell_planning",
    "artifact_summary",
]


class CapabilityRouterService:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        matrix: WorkspacePermissionMatrixService | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "capability_router.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.matrix = matrix or WorkspacePermissionMatrixService().load()
        self.models = ModelRegistryService()
        self.providers = ProviderRegistryService()

    def capabilities(self) -> list[dict[str, Any]]:
        configured = self.config.get("capabilities", {}) if isinstance(self.config.get("capabilities"), dict) else {}
        return [self._capability_payload(capability_id, configured.get(capability_id, {})) for capability_id in CORE_CAPABILITIES]

    def health(self) -> dict[str, Any]:
        items = [self._health_for(item) for item in self.capabilities()]
        status = "ok" if all(item["health_status"] in {"ok", "disabled", "missing", "unverified"} for item in items) else "degraded"
        return {
            "status": status,
            "capabilities": items,
            "summary": {
                "ok": sum(1 for item in items if item["health_status"] == "ok"),
                "missing": sum(1 for item in items if item["health_status"] == "missing"),
                "disabled": sum(1 for item in items if item["health_status"] == "disabled"),
                "unverified": sum(1 for item in items if item["health_status"] == "unverified"),
                "failed": sum(1 for item in items if item["health_status"] == "failed"),
            },
        }

    def model_registry(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "models": [model.model_dump() for model in self.models.list_models()],
            "providers": [provider.model_dump() for provider in self.providers.list_providers()],
        }

    def router_rules(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "config_path": str(self.config_path),
            "route_matrix": self.config.get("route_matrix", {}),
            "roles": self.config.get("roles", {}),
        }

    def route_preview(self, *, operation_type: str, intent_type: str | None = None, source_channel: str = "api") -> dict[str, Any]:
        route_matrix = self.config.get("route_matrix", {}) if isinstance(self.config.get("route_matrix"), dict) else {}
        required = list(route_matrix.get(operation_type) or route_matrix.get(intent_type or "") or route_matrix.get("chat") or ["text_chat"])
        selected = [self._health_for(self._capability_by_id(capability_id)) for capability_id in required]
        fallback_used = any(item["health_status"] in {"missing", "disabled", "failed"} for item in selected)
        decision = {
            "operation_id": f"model_route_{uuid4().hex}",
            "operation_type": operation_type,
            "intent_type": intent_type,
            "source_channel": source_channel,
            "required_capabilities": required,
            "selected_capabilities": selected,
            "fallback_used": fallback_used,
            "reason": "capability_route_preview",
            "confidence": "medium" if fallback_used else "high",
        }
        self.record_route_decision(decision)
        return {"status": "ok", "route_decision": decision}

    def test_capability(self, capability: str, input_value: Any = None) -> dict[str, Any]:
        item = self._health_for(self._capability_by_id(capability))
        start = datetime.now(timezone.utc)
        result_summary: dict[str, Any] = {}
        status = item["health_status"]
        if capability == "embeddings" and status == "ok":
            result_summary = {"vector_available": False, "reason": "runtime_health_ok_but_direct_embedding_call_not_executed_in_health_test"}
            status = "unverified"
        elif capability == "reranker" and status == "ok":
            result_summary = {"reranker_available": False, "reason": "runtime_health_ok_but_direct_rerank_call_not_executed_in_health_test"}
            status = "unverified"
        elif capability == "workspace_search":
            result_summary = {"fallback": "keyword_search", "query": str(input_value or "")[:120]}
            status = "ok"
        elif status == "disabled":
            result_summary = {"reason": "capability_disabled_by_config"}
        elif status == "missing":
            result_summary = {"reason": item.get("reason", "provider_or_model_missing")}
        else:
            result_summary = {"test_prompt": item.get("test_prompt")}
        latency_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        return {
            "status": status,
            "capability": capability,
            "provider": item.get("provider"),
            "model": item.get("model"),
            "latency_ms": latency_ms,
            "result_summary": result_summary,
        }

    def workspace_search(self, *, query: str, workspace_path: str, limit: int = 10) -> dict[str, Any]:
        decision = self.matrix.decide(path=workspace_path, permission="list_files")
        if decision.status == "denied":
            return {"status": "blocked", "reason_code": decision.reason_code, "policy_decision": decision.model_dump(), "results": []}
        root = Path(workspace_path).resolve(strict=False)
        if not root.exists() or not root.is_dir():
            return {"status": "failed", "reason_code": "workspace_path_not_found", "results": []}
        terms = [term.casefold() for term in re.findall(r"\w+", query) if len(term) >= 2]
        results: list[dict[str, Any]] = []
        ignored = {".git", "node_modules", ".venv", "__pycache__", "build", "dist"}
        for file_path in root.rglob("*"):
            if len(results) >= max(1, limit):
                break
            if any(part in ignored for part in file_path.parts):
                continue
            if not file_path.is_file() or file_path.stat().st_size > 512_000:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            haystack = text.casefold()
            if terms and not any(term in haystack or term in file_path.name.casefold() for term in terms):
                continue
            snippet = text[:500].replace("\r", " ").replace("\n", " ")
            results.append({"path": str(file_path), "snippet": snippet, "score": 1.0})
        route = self.route_preview(operation_type="workspace_search", source_channel="capability_router")
        return {
            "status": "ok",
            "query": query,
            "workspace_path": str(root),
            "results": results,
            "capabilities_used": {
                "workspace_search": True,
                "embeddings_used": False,
                "reranker_used": False,
                "fallback": "keyword_search",
            },
            "route_decision": route["route_decision"],
        }

    def record_route_decision(self, decision: dict[str, Any]) -> None:
        event = {
            "event_id": f"event_{uuid4().hex}",
            "event_type": "model_route_decision",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": decision,
        }
        path = PATHS.project_root / "data" / "runtime" / "model_route_decisions.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _capability_by_id(self, capability_id: str) -> dict[str, Any]:
        configured = self.config.get("capabilities", {}) if isinstance(self.config.get("capabilities"), dict) else {}
        return self._capability_payload(capability_id, configured.get(capability_id, {}))

    def _capability_payload(self, capability_id: str, raw: Any) -> dict[str, Any]:
        payload = dict(raw) if isinstance(raw, dict) else {}
        payload.setdefault("capability_id", capability_id)
        payload.setdefault("enabled", False)
        payload.setdefault("provider", None)
        payload.setdefault("model", None)
        payload.setdefault("endpoint", None)
        payload.setdefault("local", True)
        payload.setdefault("requires_api_key", False)
        payload.setdefault("cost_profile", "unknown")
        payload.setdefault("privacy_profile", "unknown")
        payload.setdefault("max_input", None)
        payload.setdefault("fallback_chain", [])
        payload.setdefault("health_status", "unverified")
        payload.setdefault("last_checked_at", None)
        payload.setdefault("test_prompt", "")
        payload.setdefault("supported_inputs", [])
        payload.setdefault("supported_outputs", [])
        return payload

    def _health_for(self, item: dict[str, Any]) -> dict[str, Any]:
        checked = dict(item)
        checked["last_checked_at"] = datetime.now(timezone.utc).isoformat()
        if not checked.get("enabled"):
            checked["health_status"] = "disabled"
            checked["reason"] = "disabled_by_config"
            return checked
        capability_id = str(checked.get("capability_id"))
        if capability_id in {"embeddings", "reranker"}:
            vector_status = VectorRAGStatusService().status()
            key = "embedding_runtime_enabled" if capability_id == "embeddings" else "reranker_runtime_enabled"
            if not bool(vector_status.get(key)):
                checked["health_status"] = "missing"
                checked["reason"] = f"{capability_id}_runtime_not_available"
            elif vector_status.get("status") == "ok":
                checked["health_status"] = "ok"
                checked["reason"] = "vector_rag_runtime_reports_ok"
            else:
                checked["health_status"] = "unverified"
                checked["reason"] = "vector_rag_runtime_degraded"
            return checked
        provider = str(checked.get("provider") or "")
        model = checked.get("model")
        if provider in {"aipinho_internal", "continue_adapter", "policy_deterministic", "local_embedding_runtime", "local_reranker_runtime"}:
            checked["health_status"] = "ok"
            checked["reason"] = "internal_or_adapter_available"
            return checked
        if model and self.models.get_model(str(model)) is None:
            checked["health_status"] = "missing"
            checked["reason"] = "configured_model_not_in_registry"
            return checked
        if provider and self.providers.get_provider(provider) is None:
            checked["health_status"] = "missing"
            checked["reason"] = "configured_provider_not_in_registry"
            return checked
        checked["health_status"] = "unverified"
        checked["reason"] = "configured_but_not_runtime_verified"
        return checked
