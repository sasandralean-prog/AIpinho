from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.patch_risk import PatchRiskAssessment
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class PatchPlanStore:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "patch_store_policy.yaml", critical=True, root=PATHS.config_root / "patching")
        configured = str((self.policy.get("store", {}) or {}).get("path", "data/runtime/patch_plans"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_guard = SecretGuardService()

    def save_plan(self, plan: PatchPlan) -> PatchPlan:
        self._write(self._plan_path(plan.plan_id), plan.model_dump())
        if plan.diff_proposal is not None:
            self.save_diff(plan.plan_id, plan.diff_proposal)
        self.save_evidence(plan.plan_id, plan.evidence)
        self.save_risk(plan.plan_id, plan.risk)
        self.save_trace(plan.plan_id, plan.trace)
        return plan

    def get_plan(self, plan_id: str) -> PatchPlan | None:
        data = self._read(self._plan_path(plan_id))
        return PatchPlan.model_validate(data) if data else None

    def list_plans(self, *, status: str | None = None, risk_level: str | None = None, source_type: str | None = None, workspace: str | None = None, limit: int = 100) -> list[PatchPlan]:
        plans: list[PatchPlan] = []
        root = self.root / "plans"
        if not root.exists():
            return []
        for path in root.glob("patch_plan_*.json"):
            try:
                plan = PatchPlan.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
            except Exception:
                continue
            if status and plan.status != status:
                continue
            if risk_level and plan.risk.risk_level != risk_level:
                continue
            if source_type and plan.source_type != source_type:
                continue
            if workspace and plan.workspace != workspace:
                continue
            plans.append(plan)
        return sorted(plans, key=lambda item: item.created_at, reverse=True)[: max(1, min(limit, 1000))]

    def save_diff(self, plan_id: str, diff: DiffProposal) -> None:
        self._write(self._diff_path(plan_id), diff.model_dump())

    def get_diff(self, plan_id: str) -> DiffProposal | None:
        data = self._read(self._diff_path(plan_id))
        return DiffProposal.model_validate(data) if data else None

    def save_evidence(self, plan_id: str, evidence: list[PatchEvidence]) -> None:
        self._write(self._evidence_path(plan_id), [item.model_dump() for item in evidence])

    def get_evidence(self, plan_id: str) -> list[PatchEvidence]:
        data = self._read(self._evidence_path(plan_id)) or []
        return [PatchEvidence.model_validate(item) for item in data if isinstance(item, dict)]

    def save_risk(self, plan_id: str, risk: PatchRiskAssessment) -> None:
        self._write(self._risk_path(plan_id), risk.model_dump())

    def get_risk(self, plan_id: str) -> PatchRiskAssessment | None:
        data = self._read(self._risk_path(plan_id))
        return PatchRiskAssessment.model_validate(data) if data else None

    def save_trace(self, plan_id: str, trace: list[str]) -> None:
        self._write(self._trace_path(plan_id), trace)

    def get_trace(self, plan_id: str) -> list[str]:
        data = self._read(self._trace_path(plan_id)) or []
        return [str(item) for item in data]

    def sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): self.sanitize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str):
            return self.secret_guard.redact(value)[0]
        return value

    def _plan_path(self, plan_id: str) -> Path:
        self._validate_id(plan_id)
        return resolve_within_root(self.root / "plans" / f"{plan_id}.json", self.root)

    def _diff_path(self, plan_id: str) -> Path:
        self._validate_id(plan_id)
        return resolve_within_root(self.root / "diffs" / f"{plan_id}.diff.json", self.root)

    def _evidence_path(self, plan_id: str) -> Path:
        self._validate_id(plan_id)
        return resolve_within_root(self.root / "evidence" / f"{plan_id}.evidence.json", self.root)

    def _risk_path(self, plan_id: str) -> Path:
        self._validate_id(plan_id)
        return resolve_within_root(self.root / "risk" / f"{plan_id}.risk.json", self.root)

    def _trace_path(self, plan_id: str) -> Path:
        self._validate_id(plan_id)
        return resolve_within_root(self.root / "trace" / f"{plan_id}.trace.json", self.root)

    def _validate_id(self, plan_id: str) -> None:
        if not re.fullmatch(r"patch_plan_[a-f0-9]+", plan_id):
            raise ValueError("invalid_patch_plan_id")

    def _write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.sanitize(value), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _read(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def status(self) -> dict[str, object]:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "service": "patch_plan_store", "path": str(self.root), "workspace_write_enabled": False}
