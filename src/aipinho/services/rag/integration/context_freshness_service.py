from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.rag.integration.contracts import ContextFreshness, ContextInjectionItem
from aipinho.services.rag.integration.config import integration_config


class ContextFreshnessService:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or integration_config("context_freshness_policy.yaml")

    def check(self, items: list[ContextInjectionItem]) -> ContextFreshness:
        warnings: list[str] = []
        blocked: list[str] = []
        statuses: dict[str, str] = {}
        memory_age = int((self.config.get("memory") or {}).get("warn_if_older_than_days", 90))
        for item in items:
            status = str(item.metadata.get("memory_status") or item.metadata.get("status") or "active")
            statuses[item.context_item_id] = status
            if item.kind == "curated_memory":
                if status in {"expired", "rejected", "superseded"}:
                    blocked.append(f"{item.context_item_id}:memory_{status}")
                created_at = item.metadata.get("created_at")
                if created_at and self._age_days(str(created_at)) > memory_age:
                    warnings.append(f"{item.context_item_id}:old_memory")
            retrieval_status = str(item.metadata.get("retrieval_status") or "")
            if retrieval_status in {"partial", "degraded"}:
                warnings.append(f"{item.context_item_id}:retrieval_{retrieval_status}")
            quality = str(item.metadata.get("quality_status") or "")
            if item.kind == "report_section" and quality and quality not in {"passed", "passed_with_warnings"}:
                warnings.append(f"{item.context_item_id}:report_quality_{quality}")
        status = "blocked" if blocked else ("stale_warning" if warnings else "fresh")
        return ContextFreshness(status=status, item_statuses=statuses, warnings=warnings, blocked_reasons=blocked)

    def _age_days(self, value: str) -> int:
        try:
            created = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return max(0, (datetime.now(timezone.utc) - created).days)
        except ValueError:
            return 0

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_freshness", "inactive_memory_blocked": True}
