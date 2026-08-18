from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.pinhoforge_bridge.command_catalog import (
    PinhoForgeCommandCatalogQuery,
    PinhoForgeCommandCatalogResult,
    PinhoForgeCommandPreviewRequest,
)
from aipinho.utils.yaml_loader import load_yaml_file


class PinhoForgeCommandCatalogProvider:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_command_catalog.yaml"
        self.root = root or PATHS.project_root

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def search(self, query: PinhoForgeCommandCatalogQuery) -> PinhoForgeCommandCatalogResult:
        items = self._commands()
        normalized_query = query.query.strip().lower()
        risks = {item.lower() for item in query.risks}
        categories = {item.lower() for item in query.categories}
        tags = {item.lower() for item in query.tags}
        collections = {item.lower() for item in query.collections}
        results = []
        for item in items:
            risk = self._normalize_risk(item.get("risk"))
            searchable = " ".join(str(item.get(key, "")) for key in ("command_id", "title", "description", "category", "collection", "body")).lower()
            searchable = f"{searchable} {' '.join(str(tag).lower() for tag in item.get('tags') or [])}"
            if normalized_query and normalized_query not in searchable:
                continue
            if categories and str(item.get("category", "")).lower() not in categories:
                continue
            if collections and str(item.get("collection", "")).lower() not in collections:
                continue
            if tags and tags.isdisjoint({str(tag).lower() for tag in item.get("tags") or []}):
                continue
            if risks and risk["label"] not in risks:
                continue
            if risk["label"] == "dangerous" and not query.include_dangerous:
                continue
            if risk["blocked"] and not query.include_blocked:
                continue
            results.append(self._public_item(item, risk))
            if len(results) >= max(1, min(query.max_results, 200)):
                break
        return PinhoForgeCommandCatalogResult(
            request_id=query.request_id,
            operation="search",
            status="completed",
            human_message="Catalogo PinhoForge consultado em modo read-only.",
            results=results,
        )

    def preview(self, request: PinhoForgeCommandPreviewRequest) -> PinhoForgeCommandCatalogResult:
        item = next((command for command in self._commands() if command.get("command_id") == request.command_id), None)
        if item is None:
            return self._blocked(request.request_id, "command_not_found", "Comando nao encontrado no catalogo.")
        if any(self._has_injection_risk(value) for value in request.parameters.values()):
            return self._blocked(request.request_id, "command_parameter_injection_blocked", "Parametro rejeitado por risco de injecao.")
        risk = self._normalize_risk(item.get("risk"))
        rendered = self._render(str(item.get("body") or ""), request.parameters)
        return PinhoForgeCommandCatalogResult(
            request_id=request.request_id,
            operation="preview",
            status="blocked" if risk["blocked"] else "preview_created",
            reason_code="dangerous_command_preview_blocked" if risk["blocked"] else None,
            human_message=(
                "Comando perigoso identificado; preview permanece bloqueado."
                if risk["blocked"]
                else "Preview de comando criado sem execucao."
            ),
            preview={
                "command_id": item.get("command_id"),
                "title": item.get("title"),
                "rendered_command_sanitized": rendered,
                "risk": risk["label"],
                "blocked": risk["blocked"],
                "execution_enabled": False,
                "safe_next_step": "Use o shell governado oficial para uma execucao real.",
            },
            execution_enabled=False,
        )

    def execute_blocked(self, request_id: str) -> PinhoForgeCommandCatalogResult:
        return self._blocked(request_id, "command_catalog_execution_disabled", "Execucao direta pelo catalogo esta bloqueada.")

    def _commands(self) -> list[dict[str, Any]]:
        provider = self.config().get("provider") or {}
        return list(provider.get("commands") or [])

    def _public_item(self, item: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
        return {
            "command_id": item.get("command_id"),
            "title": item.get("title"),
            "category": item.get("category"),
            "collection": item.get("collection"),
            "tags": item.get("tags") or [],
            "risk": risk["label"],
            "blocked": risk["blocked"],
            "description": item.get("description"),
            "execution_enabled": False,
        }

    def _normalize_risk(self, risk: Any) -> dict[str, Any]:
        label = str(risk or "unknown").strip().lower()
        if label in {"safe", "low"}:
            return {"label": "safe", "blocked": False}
        if label in {"caution", "medium", "warning"}:
            return {"label": "caution", "blocked": False}
        if label in {"danger", "dangerous", "high", "critical", "unknown"}:
            return {"label": "dangerous" if label != "unknown" else "unknown", "blocked": True}
        return {"label": "unknown", "blocked": True}

    def _has_injection_risk(self, value: str) -> bool:
        return any(token in value for token in (";", "&&", "||", "|", "`", "$(", ">", "<", "\n", "\r"))

    def _render(self, template: str, parameters: dict[str, str]) -> str:
        rendered = template
        for key, value in parameters.items():
            rendered = rendered.replace(f"<{key}>", value).replace(f"{{{{{key}}}}}", value).replace("${" + key + "}", value)
        return rendered

    def _blocked(self, request_id: str, reason_code: str, message: str) -> PinhoForgeCommandCatalogResult:
        return PinhoForgeCommandCatalogResult(
            request_id=request_id,
            operation="blocked",
            status="blocked",
            reason_code=reason_code,
            human_message=message,
            execution_enabled=False,
        )
