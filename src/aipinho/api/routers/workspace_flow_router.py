from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from aipinho.schemas.common.actor import Actor
from aipinho.schemas.workspace_flows.workspace_flow import WorkspaceFlowPlanRequest
from aipinho.services.security.local_token_service import LocalTokenService
from aipinho.services.workspace_flows.workspace_flow_service import WorkspaceFlowService

router = APIRouter(prefix="/api/v1/workspace-flows", tags=["workspace-flows"])


def _service() -> WorkspaceFlowService:
    return WorkspaceFlowService()


def _require_token(authorization: str | None) -> None:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")


def _raise_value_error(exc: ValueError) -> None:
    detail = str(exc)
    status = 404 if detail.endswith("_not_found") else 409
    raise HTTPException(status_code=status, detail=detail) from exc


@router.get("/rules")
def list_rules() -> dict[str, object]:
    return {"status": "ok", "rules": [rule.model_dump() for rule in _service().list_rules()]}


@router.post("/rules")
def create_rule(payload: dict[str, object], authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    rule = _service().create_rule(payload)
    return {"status": "ok", "rule": rule.model_dump()}


@router.get("/rules/{flow_id}")
def get_rule(flow_id: str) -> dict[str, object]:
    rule = _service().get_rule(flow_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="workspace_flow_rule_not_found")
    return {"status": "ok", "rule": rule.model_dump()}


@router.patch("/rules/{flow_id}")
def update_rule(flow_id: str, payload: dict[str, object], authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        rule = _service().update_rule(flow_id, payload)
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok", "rule": rule.model_dump()}


@router.post("/plan")
def create_plan(request: WorkspaceFlowPlanRequest) -> dict[str, object]:
    plan = _service().plan(request)
    return {"status": "ok" if plan.status != "blocked" else "blocked", "plan": plan.model_dump()}


@router.get("/plans/{flow_plan_id}")
def get_plan(flow_plan_id: str) -> dict[str, object]:
    plan = _service().get_plan(flow_plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="workspace_flow_plan_not_found")
    return {"status": "ok", "plan": plan.model_dump()}


@router.post("/plans/{flow_plan_id}/approve")
def approve_plan(flow_plan_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        plan = _service().approve_plan(flow_plan_id, actor=Actor(type="user", id="local_user"))
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok", "plan": plan.model_dump()}


@router.post("/plans/{flow_plan_id}/deny")
def deny_plan(flow_plan_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        plan = _service().deny_plan(flow_plan_id, actor=Actor(type="user", id="local_user"))
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok", "plan": plan.model_dump()}


@router.post("/plans/{flow_plan_id}/execute")
def execute_plan(flow_plan_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _require_token(authorization)
    try:
        result = _service().execute_plan(flow_plan_id)
    except ValueError as exc:
        _raise_value_error(exc)
    return {"status": "ok" if result.status == "completed" else result.status, "result": result.model_dump()}


@router.get("/plans/by-run/{run_id}")
def list_plans_by_run(run_id: str) -> dict[str, object]:
    return {"status": "ok", "plans": [plan.model_dump() for plan in _service().list_plans_by_run(run_id)]}
