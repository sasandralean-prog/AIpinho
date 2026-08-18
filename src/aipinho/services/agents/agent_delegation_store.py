from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.delegation import DelegationPolicyDecision, DelegationRequest, DelegationResult
from aipinho.schemas.events.contracts import utc_now_iso


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


class AgentDelegationStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_AGENT_DELEGATION_ROOT")
        base = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "agent_kernel" / "delegations")
        self.root = base
        self.requests_dir = self.root / "requests"
        self.decisions_dir = self.root / "policy_decisions"
        self.results_dir = self.root / "results"

    def save_request(self, request: DelegationRequest) -> DelegationRequest:
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        payload = request.model_copy(update={"updated_at": utc_now_iso()})
        (self.requests_dir / f"{payload.delegation_id}.json").write_text(json.dumps(_dump(payload), indent=2, ensure_ascii=True), encoding="utf-8")
        return payload

    def get_request(self, delegation_id: str) -> DelegationRequest | None:
        path = self.requests_dir / f"{delegation_id}.json"
        if not path.exists():
            return None
        return DelegationRequest(**json.loads(path.read_text(encoding="utf-8")))

    def list_requests(self, *, parent_run_id: str | None = None, child_run_id: str | None = None) -> list[DelegationRequest]:
        if not self.requests_dir.exists():
            return []
        rows = [DelegationRequest(**json.loads(path.read_text(encoding="utf-8"))) for path in self.requests_dir.glob("*.json")]
        if parent_run_id is not None:
            rows = [item for item in rows if item.parent_run_id == parent_run_id]
        if child_run_id is not None:
            rows = [item for item in rows if item.child_run_id == child_run_id]
        return sorted(rows, key=lambda item: item.created_at, reverse=True)

    def save_policy_decision(self, decision: DelegationPolicyDecision) -> DelegationPolicyDecision:
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        (self.decisions_dir / f"{decision.delegation_id}.json").write_text(json.dumps(_dump(decision), indent=2, ensure_ascii=True), encoding="utf-8")
        return decision

    def get_policy_decision(self, delegation_id: str) -> DelegationPolicyDecision | None:
        path = self.decisions_dir / f"{delegation_id}.json"
        if not path.exists():
            return None
        return DelegationPolicyDecision(**json.loads(path.read_text(encoding="utf-8")))

    def save_result(self, result: DelegationResult) -> DelegationResult:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        (self.results_dir / f"{result.delegation_id}.json").write_text(json.dumps(_dump(result), indent=2, ensure_ascii=True), encoding="utf-8")
        return result

    def get_result(self, delegation_id: str) -> DelegationResult | None:
        path = self.results_dir / f"{delegation_id}.json"
        if not path.exists():
            return None
        return DelegationResult(**json.loads(path.read_text(encoding="utf-8")))
