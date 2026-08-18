from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.policy_kernel import AutoApprovalDecision
from aipinho.schemas.agents.tool_gateway import PolicyDecision


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


class MultiAgentPolicyAuditStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_POLICY_KERNEL_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "multi_agent_policy_kernel")
        self.decisions_dir = self.root / "decisions"
        self.auto_dir = self.root / "auto_approvals"

    def save_policy_decision(self, decision: PolicyDecision) -> PolicyDecision:
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        (self.decisions_dir / f"{decision.policy_decision_id}.json").write_text(
            json.dumps(_dump_model(decision), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return decision

    def get_policy_decision(self, policy_decision_id: str) -> PolicyDecision | None:
        path = self.decisions_dir / f"{policy_decision_id}.json"
        if not path.exists():
            return None
        return PolicyDecision(**json.loads(path.read_text(encoding="utf-8")))

    def list_policy_decisions(
        self,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> list[PolicyDecision]:
        if not self.decisions_dir.exists():
            return []
        rows = [
            PolicyDecision(**json.loads(path.read_text(encoding="utf-8")))
            for path in self.decisions_dir.glob("*.json")
        ]
        if agent_id is not None:
            rows = [row for row in rows if row.agent_id == agent_id]
        if session_id is not None:
            rows = [row for row in rows if row.session_id == session_id]
        if run_id is not None:
            rows = [row for row in rows if row.run_id == run_id]
        return sorted(rows, key=lambda row: row.created_at, reverse=True)

    def save_auto_approval(self, decision: AutoApprovalDecision) -> AutoApprovalDecision:
        self.auto_dir.mkdir(parents=True, exist_ok=True)
        (self.auto_dir / f"{decision.auto_approval_id}.json").write_text(
            json.dumps(_dump_model(decision), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return decision

    def get_auto_approval(self, auto_approval_id: str) -> AutoApprovalDecision | None:
        path = self.auto_dir / f"{auto_approval_id}.json"
        if not path.exists():
            return None
        return AutoApprovalDecision(**json.loads(path.read_text(encoding="utf-8")))

    def list_auto_approvals(
        self,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> list[AutoApprovalDecision]:
        if not self.auto_dir.exists():
            return []
        rows = [
            AutoApprovalDecision(**json.loads(path.read_text(encoding="utf-8")))
            for path in self.auto_dir.glob("*.json")
        ]
        if agent_id is not None:
            rows = [row for row in rows if row.agent_id == agent_id]
        if session_id is not None:
            rows = [row for row in rows if row.session_id == session_id]
        if run_id is not None:
            rows = [row for row in rows if row.run_id == run_id]
        return sorted(rows, key=lambda row: row.created_at, reverse=True)
