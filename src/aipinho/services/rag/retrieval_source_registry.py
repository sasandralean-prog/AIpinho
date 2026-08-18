from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.retrieval_request import RetrievalSource
from aipinho.utils.yaml_loader import load_yaml_file


class RetrievalSourceRegistry:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or load_yaml_file(PATHS.config_root / "rag" / "retrieval_source_registry.yaml", critical=True, root=PATHS.config_root / "rag")

    def list_sources(self, include_blocked: bool = False) -> list[RetrievalSource]:
        sources: list[RetrievalSource] = []
        for source_id, data in (self.config.get("sources") or {}).items():
            sources.append(self._source_from_config(source_id, data))
        if include_blocked:
            for source_id, data in (self.config.get("blocked_sources") or {}).items():
                payload = dict(data or {})
                payload.setdefault("source_type", source_id)
                payload.setdefault("adapter", source_id)
                payload.setdefault("read_only", False)
                payload.setdefault("enabled", False)
                sources.append(self._source_from_config(source_id, payload))
        return sources

    def get_source(self, source_id: str) -> RetrievalSource | None:
        data = (self.config.get("sources") or {}).get(source_id)
        if data is not None:
            return self._source_from_config(source_id, data)
        blocked = (self.config.get("blocked_sources") or {}).get(source_id)
        if blocked is not None:
            payload = dict(blocked)
            payload.setdefault("source_type", source_id)
            payload.setdefault("adapter", source_id)
            payload.setdefault("enabled", False)
            payload.setdefault("read_only", False)
            return self._source_from_config(source_id, payload)
        return None

    def _source_from_config(self, source_id: str, data: dict) -> RetrievalSource:
        return RetrievalSource(
            source_id=source_id,
            source_type=str(data.get("source_type") or source_id),
            adapter=str(data.get("adapter") or source_id),
            enabled=bool(data.get("enabled", True)),
            read_only=bool(data.get("read_only", False)),
            requires_workspace=bool(data.get("requires_workspace", False)),
            explicit_request_required=bool(data.get("explicit_request_required", False)),
            auto_enabled_in_chat=bool(data.get("auto_enabled_in_chat", False)),
            auto_enabled_in_prompt=bool(data.get("auto_enabled_in_prompt", False)),
            description=str(data.get("description") or ""),
            reason=data.get("reason"),
        )

    def status(self) -> dict[str, object]:
        sources = self.list_sources(include_blocked=True)
        return {
            "status": "ok",
            "service": "retrieval_source_registry",
            "source_count": len([source for source in sources if source.enabled]),
            "blocked_source_count": len([source for source in sources if not source.enabled]),
            "sources": [source.model_dump() for source in sources],
        }
