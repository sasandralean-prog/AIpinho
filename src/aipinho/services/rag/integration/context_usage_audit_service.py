from __future__ import annotations

import json
import re
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.integration.contracts import ContextInjectionPlan, ContextUsageAudit
from aipinho.services.rag.integration.config import integration_config
from aipinho.utils.safe_paths import resolve_within_root


class ContextUsageAuditService:
    def __init__(self, root: Path | None = None) -> None:
        config = integration_config("context_usage_audit_policy.yaml")
        configured = str((config.get("audit") or {}).get("store_path", "data/runtime/context/plans"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)

    def save_plan(self, plan: ContextInjectionPlan) -> ContextInjectionPlan:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = self._sanitize(plan.model_dump())
        self._path(plan.plan_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return plan

    def get_plan(self, plan_id: str) -> ContextInjectionPlan | None:
        path = self._path(plan_id)
        if not path.exists():
            return None
        return ContextInjectionPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_plans(self, limit: int = 100) -> list[ContextInjectionPlan]:
        if not self.root.exists():
            return []
        plans: list[ContextInjectionPlan] = []
        for path in sorted(self.root.glob("context_plan_*.json"), reverse=True):
            try:
                plans.append(ContextInjectionPlan.model_validate(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(plans) >= max(1, min(limit, 1000)):
                break
        return plans

    def audit_for(self, plan: ContextInjectionPlan) -> ContextUsageAudit:
        return ContextUsageAudit(
            subject_id=plan.plan_id,
            subject_type="context_injection_plan",
            status=plan.status,
            warnings=plan.warnings,
            blocked_reasons=plan.blocked_reasons,
        )

    def _path(self, plan_id: str) -> Path:
        if not re.fullmatch(r"context_plan_[a-f0-9]+", plan_id):
            raise ValueError("invalid_context_plan_id")
        return resolve_within_root(self.root / f"{plan_id}.json", self.root)

    def _sanitize(self, value):
        if isinstance(value, dict):
            return {key: self._sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if isinstance(value, str):
            return re.sub(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", value)
        return value

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_usage_audit", "raw_context_saved": False}
