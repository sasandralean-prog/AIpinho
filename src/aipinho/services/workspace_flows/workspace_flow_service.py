from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.workspace_flows.workspace_flow import (
    WorkspaceFlowEndpoint,
    WorkspaceFlowExecutionResult,
    WorkspaceFlowPlan,
    WorkspaceFlowPlanRequest,
    WorkspaceFlowRule,
    WorkspaceFlowStep,
)
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkspaceFlowService:
    OPERATION_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
        "copy_file": {"source": ["read_file", "copy_from"], "target": ["create_file", "copy_to"]},
        "move_file": {"source": ["read_file", "copy_from", "delete_file", "move_from"], "target": ["create_file", "copy_to", "move_to"]},
        "import_file": {"source": ["read_file", "copy_from"], "target": ["create_file", "copy_to"]},
        "download_to_staging": {"source": [], "target": ["network_download", "create_file"]},
        "apply_asset_to_project": {"source": ["read_file", "copy_from"], "target": ["create_file", "copy_to"]},
        "read_from_source_apply_to_target": {"source": ["read_file"], "target": ["modify_file", "apply_patch"]},
        "git_push": {"source": ["git_push"], "target": []},
        "delete_file": {"source": ["delete_file"], "target": []},
    }

    RISK_LEVELS = {
        "copy_file": "low",
        "import_file": "low",
        "download_to_staging": "medium",
        "apply_asset_to_project": "medium",
        "read_from_source_apply_to_target": "medium",
        "move_file": "high",
        "delete_file": "high",
        "git_push": "high",
    }

    def __init__(
        self,
        *,
        data_root: Path | None = None,
        matrix: WorkspacePermissionMatrixService | None = None,
        approvals: ApprovalService | None = None,
        staging_root: Path | None = None,
    ) -> None:
        self.data_root = data_root or PATHS.project_root / "data" / "runtime" / "workspace_flows"
        self.rules_root = self.data_root / "rules"
        self.plans_root = self.data_root / "plans"
        self.events_path = self.data_root / "events.jsonl"
        self.matrix = matrix or WorkspacePermissionMatrixService().load()
        self.approvals = approvals or ApprovalService()
        self.staging_root = staging_root or PATHS.project_root / "staging"

    def list_rules(self) -> list[WorkspaceFlowRule]:
        self.rules_root.mkdir(parents=True, exist_ok=True)
        rules: list[WorkspaceFlowRule] = []
        for path in sorted(self.rules_root.glob("*.json")):
            try:
                rules.append(WorkspaceFlowRule(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return rules

    def create_rule(self, payload: dict[str, object]) -> WorkspaceFlowRule:
        now = _utc_now()
        rule = WorkspaceFlowRule(flow_id=f"flow_{uuid4().hex}", created_at=now, updated_at=now, **payload)
        self._save_rule(rule)
        return rule

    def get_rule(self, flow_id: str) -> WorkspaceFlowRule | None:
        path = self.rules_root / f"{flow_id}.json"
        if not path.exists():
            return None
        return WorkspaceFlowRule(**json.loads(path.read_text(encoding="utf-8")))

    def update_rule(self, flow_id: str, payload: dict[str, object]) -> WorkspaceFlowRule:
        rule = self.get_rule(flow_id)
        if rule is None:
            raise ValueError("workspace_flow_rule_not_found")
        updated = WorkspaceFlowRule(**{**rule.model_dump(), **payload, "flow_id": flow_id, "updated_at": _utc_now()})
        self._save_rule(updated)
        return updated

    def plan(self, request: WorkspaceFlowPlanRequest) -> WorkspaceFlowPlan:
        requirements = self.OPERATION_REQUIREMENTS[request.operation]
        source_path = self._source_path(request)
        target_path = self._target_path(request)
        source_endpoint, source_reasons, source_ask = self._endpoint("source", source_path, requirements["source"])
        target_endpoint, target_reasons, target_ask = self._endpoint("target", target_path, requirements["target"]) if target_path else (None, [], False)
        reason_codes = [*source_reasons, *target_reasons]
        requires_approval = source_ask or target_ask or request.operation in {"move_file", "delete_file", "git_push", "download_to_staging"}
        status = "blocked" if any("permission_denied" in item or "not_registered" in item or "disabled" in item for item in reason_codes) else "planned"
        plan = WorkspaceFlowPlan(
            flow_plan_id=f"flow_plan_{uuid4().hex}",
            run_id=request.run_id,
            task_id=request.task_id,
            operation=request.operation,
            source=source_endpoint,
            target=target_endpoint,
            steps=self._steps_for(request, source_path, target_path),
            risk_level=self.RISK_LEVELS.get(request.operation, "medium"),  # type: ignore[arg-type]
            requires_approval=requires_approval,
            status=status,
            reason_codes=reason_codes,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        self._append_event("workspace_flow_plan_created", plan, {"status": plan.status})
        for reason in reason_codes:
            self._append_event("workspace_flow_permission_checked", plan, {"reason_code": reason})
        if plan.status != "blocked" and requires_approval:
            approval = self._create_approval(plan)
            plan.approval_id = approval.approval_id
            plan.status = "pending_approval"
            plan.steps = [
                self._copy_step(step, requires_approval=True, approval_id=approval.approval_id)
                for step in plan.steps
            ]
            self._append_event("workspace_flow_approval_required", plan, {"approval_id": approval.approval_id})
        self._save_plan(plan)
        return plan

    def get_plan(self, flow_plan_id: str) -> WorkspaceFlowPlan | None:
        path = self.plans_root / f"{flow_plan_id}.json"
        if not path.exists():
            return None
        return WorkspaceFlowPlan(**json.loads(path.read_text(encoding="utf-8")))

    def list_plans_by_run(self, run_id: str) -> list[WorkspaceFlowPlan]:
        self.plans_root.mkdir(parents=True, exist_ok=True)
        plans: list[WorkspaceFlowPlan] = []
        for path in sorted(self.plans_root.glob("*.json")):
            try:
                plan = WorkspaceFlowPlan(**json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            if plan.run_id == run_id:
                plans.append(plan)
        return plans

    def approve_plan(self, flow_plan_id: str, actor: Actor | None = None) -> WorkspaceFlowPlan:
        plan = self._require_plan(flow_plan_id)
        if plan.approval_id:
            self.approvals.approve(plan.approval_id, actor=actor or Actor(type="user", id="local_user"), reason="workspace_flow_approved")
        plan.status = "approved"
        plan.updated_at = _utc_now()
        plan.steps = [self._copy_step(step, status="approved") for step in plan.steps]
        self._append_event("workspace_flow_approved", plan, {"approval_id": plan.approval_id})
        self._save_plan(plan)
        return plan

    def deny_plan(self, flow_plan_id: str, actor: Actor | None = None) -> WorkspaceFlowPlan:
        plan = self._require_plan(flow_plan_id)
        if plan.approval_id:
            self.approvals.reject(plan.approval_id, actor=actor or Actor(type="user", id="local_user"), reason="workspace_flow_denied")
        plan.status = "cancelled"
        plan.updated_at = _utc_now()
        plan.steps = [self._copy_step(step, status="skipped") for step in plan.steps]
        self._append_event("workspace_flow_denied", plan, {"approval_id": plan.approval_id})
        self._save_plan(plan)
        return plan

    def execute_plan(self, flow_plan_id: str) -> WorkspaceFlowExecutionResult:
        plan = self._require_plan(flow_plan_id)
        if plan.status == "blocked":
            return WorkspaceFlowExecutionResult(flow_plan_id=flow_plan_id, status="blocked", reason_code="flow_blocked_by_policy")
        if plan.requires_approval:
            approval = self.approvals.get_approval(plan.approval_id) if plan.approval_id else None
            if approval is None or approval.status != "approved":
                return WorkspaceFlowExecutionResult(flow_plan_id=flow_plan_id, status="pending_approval", reason_code="approval_missing")
        if plan.operation in {"git_push", "download_to_staging"}:
            return WorkspaceFlowExecutionResult(flow_plan_id=flow_plan_id, status="failed", reason_code=f"{plan.operation}_requires_external_executor")
        plan.status = "running"
        plan.updated_at = _utc_now()
        self._append_event("workspace_flow_execution_started", plan, {})
        completed: list[str] = []
        try:
            if plan.operation in {"copy_file", "import_file", "apply_asset_to_project"}:
                self._copy_and_validate(plan)
                completed = [step.step_id for step in plan.steps]
            elif plan.operation == "move_file":
                self._copy_and_validate(plan)
                completed = [step.step_id for step in plan.steps if step.operation != "delete_file"]
                self._delete_source_after_validation(plan)
                completed = [step.step_id for step in plan.steps]
            elif plan.operation == "delete_file":
                self._delete_source_after_validation(plan, copy_required=False)
                completed = [step.step_id for step in plan.steps]
            else:
                raise ValueError("unsupported_workspace_flow_operation")
            plan.status = "completed"
            plan.steps = [self._copy_step(step, status="completed") for step in plan.steps]
            self._append_event("workspace_flow_completed", plan, {"completed_steps": completed})
            result = WorkspaceFlowExecutionResult(flow_plan_id=flow_plan_id, status="completed", completed_steps=completed, evidence_refs=plan.evidence_refs)
        except Exception as exc:
            plan.status = "failed"
            self._append_event("workspace_flow_failed", plan, {"error": str(exc)})
            result = WorkspaceFlowExecutionResult(flow_plan_id=flow_plan_id, status="failed", reason_code=str(exc), completed_steps=completed)
        plan.updated_at = _utc_now()
        self._save_plan(plan)
        return result

    def _source_path(self, request: WorkspaceFlowPlanRequest) -> str | None:
        if request.operation == "download_to_staging":
            return request.source_path or self._path_from_endpoint(request.source) or str(request.metadata.get("url") or "")
        return request.source_path or self._path_from_endpoint(request.source)

    def _target_path(self, request: WorkspaceFlowPlanRequest) -> str | None:
        if request.operation == "download_to_staging" and not request.target_path and request.target is None:
            filename = str(request.metadata.get("filename") or "downloaded_file")
            return str(self.staging_root / filename)
        return request.target_path or self._path_from_endpoint(request.target)

    def _path_from_endpoint(self, endpoint: WorkspaceFlowEndpoint | None) -> str | None:
        if endpoint is None:
            return None
        path = str(endpoint.path or "").strip()
        workspace_id = str(endpoint.workspace_id or "").strip()
        if workspace_id:
            workspace = self.matrix.get_workspace(workspace_id)
            if workspace is not None:
                root_path = str(workspace.get("root_path") or "").strip()
                if root_path and (not path or not Path(path).is_absolute()):
                    return str(Path(root_path) / path) if path else root_path
        return path or None

    def _endpoint(self, side: str, path: str | None, permissions: list[str]) -> tuple[WorkspaceFlowEndpoint | None, list[str], bool]:
        if not permissions:
            return (WorkspaceFlowEndpoint(path=path or "", required_permissions=[]), [], False) if path else (None, [], False)
        if not path:
            return None, [f"{side}_path_missing"], False
        decisions = [self.matrix.decide(path=path, permission=permission) for permission in permissions]
        reasons: list[str] = []
        requires_approval = False
        for decision in decisions:
            if decision.reason_code == "workspace_not_registered":
                reasons.append(f"{side}_workspace_not_registered")
            elif decision.reason_code == "workspace_disabled":
                reasons.append(f"{side}_workspace_disabled")
            elif decision.reason_code == "permission_denied":
                reasons.append(f"{side}_permission_denied:{decision.permission}")
            elif decision.reason_code == "permission_requires_approval":
                reasons.append(f"{side}_permission_requires_approval:{decision.permission}")
                requires_approval = True
        first = decisions[0] if decisions else self.matrix.decide(path=path, permission="read_file")
        endpoint = WorkspaceFlowEndpoint(
            path=path,
            workspace_id=first.workspace_id,
            role=first.workspace_role,
            required_permissions=permissions,
        )
        return endpoint, reasons, requires_approval

    def _steps_for(self, request: WorkspaceFlowPlanRequest, source_path: str | None, target_path: str | None) -> list[WorkspaceFlowStep]:
        steps: list[WorkspaceFlowStep] = []
        def add(operation: str, source: str | None = source_path, target: str | None = target_path, command: str | None = None) -> None:
            steps.append(WorkspaceFlowStep(step_id=f"flow_step_{len(steps)+1:02d}_{uuid4().hex[:8]}", operation=operation, source_path=source, target_path=target, command=command))

        if request.operation in {"copy_file", "import_file", "apply_asset_to_project"}:
            add("read_file")
            add("copy_file")
            add("validate_file")
        elif request.operation == "move_file":
            add("read_file")
            add("copy_file")
            add("validate_file")
            add("delete_file")
            add("validate_source_removed")
        elif request.operation == "delete_file":
            add("delete_file", target=None)
        elif request.operation == "git_push":
            add("git_push", command=request.command)
        elif request.operation == "download_to_staging":
            add("network_download", source=source_path, target=target_path)
            add("validate_file", source=target_path, target=target_path)
        elif request.operation == "read_from_source_apply_to_target":
            add("read_file")
            add("apply_patch")
            add("validate_file")
        return steps

    def _copy_and_validate(self, plan: WorkspaceFlowPlan) -> None:
        if plan.source is None or plan.target is None:
            raise ValueError("source_or_target_missing")
        source = Path(plan.source.path)
        target = Path(plan.target.path)
        if not source.is_file():
            raise ValueError("source_file_not_found")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._append_event("workspace_flow_step_started", plan, {"operation": "copy_file", "source_path": str(source), "target_path": str(target)})
        shutil.copy2(source, target)
        if not target.is_file() or target.stat().st_size != source.stat().st_size:
            raise ValueError("destination_validation_failed")
        source_hash = self._hash_file(source)
        target_hash = self._hash_file(target)
        if source_hash != target_hash:
            raise ValueError("destination_validation_failed")
        plan.evidence_refs.append({"type": "file_hash", "ref_id": target_hash})
        self._append_event("workspace_flow_destination_validated", plan, {"target_path": str(target), "sha256": target_hash})
        self._append_event("workspace_flow_step_completed", plan, {"operation": "copy_file", "target_path": str(target)})

    def _delete_source_after_validation(self, plan: WorkspaceFlowPlan, *, copy_required: bool = True) -> None:
        if plan.source is None:
            raise ValueError("source_missing")
        source = Path(plan.source.path)
        if copy_required:
            if plan.target is None or not Path(plan.target.path).is_file():
                raise ValueError("destination_validation_failed")
        self._append_event("workspace_flow_source_delete_requested", plan, {"source_path": str(source)})
        if not source.is_file():
            raise ValueError("source_file_not_found")
        source.unlink()
        if source.exists():
            raise ValueError("source_delete_validation_failed")
        self._append_event("workspace_flow_source_deleted", plan, {"source_path": str(source)})

    def _create_approval(self, plan: WorkspaceFlowPlan) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        requested_actions = list(dict.fromkeys(step.operation for step in plan.steps))
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=f"workspace_flow_preview_{plan.flow_plan_id}",
            draft_id=f"workspace_flow_draft_{plan.flow_plan_id}",
            run_id=plan.run_id,
            task_id=plan.task_id,
            agent_id="aipinho",
            workspace_id=plan.target.workspace_id if plan.target else plan.source.workspace_id if plan.source else None,
            workspace_path=plan.target.path if plan.target else plan.source.path if plan.source else None,
            operation_type=f"workspace_flow:{plan.operation}",
            target_paths=[plan.target.path] if plan.target else [],
            commands=[step.command for step in plan.steps if step.command],
            preview={
                "available": True,
                "summary": f"Workspace flow {plan.operation}",
                "flow_plan_id": plan.flow_plan_id,
                "source_paths": [plan.source.path] if plan.source else [],
                "target_paths": [plan.target.path] if plan.target else [],
                "steps": [step.model_dump() for step in plan.steps],
            },
            policy_refs=["workspace_flow_policy"],
            allowed_by_policy=True,
            forbidden_operations=[],
            actions_requested=requested_actions,
            approval_scope="single_action",
            reason="workspace_flow_requires_approval",
            risk_level=plan.risk_level,
            policy_snapshot=ApprovalPolicySnapshot(
                policy_decision_id=f"policy_workspace_flow_{plan.flow_plan_id}",
                policy_status="needs_approval",
                allowed_actions=requested_actions,
                denied_actions=[],
                approval_required_for=requested_actions,
                workspace_status="registered",
                risk_level=plan.risk_level,
                trace_hash=hashlib.sha256(plan.flow_plan_id.encode("utf-8")).hexdigest(),
            ),
            expires_at=(now + timedelta(hours=2)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=Actor(type="system", id="workspace_flow_service"),
            trace=[{"stage": "workspace_flow", "decision": "pending", "reason": "approval_required_before_side_effect"}],
            execution_status="not_executed",
        )
        self.approvals.store.save(approval)
        self.approvals.append_event(approval.approval_id, "approval_created", "ApprovalRequest criado para workspace flow.", {"flow_plan_id": plan.flow_plan_id})
        return approval

    def _hash_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _copy_step(self, step: WorkspaceFlowStep, **updates: object) -> WorkspaceFlowStep:
        if hasattr(step, "model_copy"):
            return step.model_copy(update=updates)
        return step.copy(update=updates)

    def _save_rule(self, rule: WorkspaceFlowRule) -> None:
        self.rules_root.mkdir(parents=True, exist_ok=True)
        (self.rules_root / f"{rule.flow_id}.json").write_text(json.dumps(rule.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_plan(self, plan: WorkspaceFlowPlan) -> None:
        self.plans_root.mkdir(parents=True, exist_ok=True)
        (self.plans_root / f"{plan.flow_plan_id}.json").write_text(json.dumps(plan.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _require_plan(self, flow_plan_id: str) -> WorkspaceFlowPlan:
        plan = self.get_plan(flow_plan_id)
        if plan is None:
            raise ValueError("workspace_flow_plan_not_found")
        return plan

    def _append_event(self, event_type: str, plan: WorkspaceFlowPlan | None, data: dict[str, object]) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        payload = {
            "event_id": f"workspace_flow_event_{uuid4().hex}",
            "event_type": event_type,
            "created_at": _utc_now(),
            "flow_plan_id": plan.flow_plan_id if plan else None,
            "run_id": plan.run_id if plan else None,
            "task_id": plan.task_id if plan else None,
            "operation": plan.operation if plan else None,
            "source_workspace_id": plan.source.workspace_id if plan and plan.source else None,
            "target_workspace_id": plan.target.workspace_id if plan and plan.target else None,
            "source_path": plan.source.path if plan and plan.source else None,
            "target_path": plan.target.path if plan and plan.target else None,
            "approval_id": plan.approval_id if plan else None,
            "status": plan.status if plan else None,
            "data": data,
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
