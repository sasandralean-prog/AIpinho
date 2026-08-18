from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.debugger.debug_trace_service import DebugTraceService
from aipinho.services.roles.role_inference_service import RoleInferenceService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_fallback_service import RoleModelFallbackService
from aipinho.services.roles.role_model_gate_service_v2 import RoleModelGateServiceV2
from aipinho.services.roles.role_model_status_service import RoleModelStatusService

router = APIRouter(prefix="/api/v1/role-models", tags=["role-models"])


def _request_for(role_id: str, request: RoleInferenceRequest | None = None, **updates) -> RoleInferenceRequest:
    base = request or RoleInferenceRequest(role_id=role_id)
    return base.model_copy(update={"role_id": role_id, **updates})


@router.get("/status")
def get_role_models_status() -> dict[str, object]:
    return RoleModelStatusService().status()


@router.get("/runs/{run_id}")
def get_role_model_run(run_id: str) -> dict[str, object]:
    run = RoleInferenceService().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="role_model_run_not_found")
    return {"status": "ok", "run": run.model_dump()}


@router.get("/runs/{run_id}/trace")
def get_role_model_run_trace(run_id: str) -> dict[str, object]:
    run = RoleInferenceService().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="role_model_run_not_found")
    trace_id = run.result.trace_id
    if not trace_id:
        return {"status": "missing", "trace": None}
    return {"status": "ok", "trace": DebugTraceService().get_trace(trace_id)}


@router.get("/runs")
def list_role_model_runs(role_id: str | None = Query(default=None), status: str | None = Query(default=None), model_id: str | None = Query(default=None)) -> dict[str, object]:
    runs = RoleInferenceService().list_runs(role_id=role_id, status=status, model_id=model_id)
    return {"status": "ok", "runs": [run.model_dump() for run in runs], "count": len(runs)}


@router.get("")
def list_role_models() -> dict[str, object]:
    service = RoleModelBindingService()
    return {
        "status": "ok",
        "roles": [binding.model_dump() for binding in service.list_bindings()],
        "disabled_until_future_sprints": [binding.model_dump() for binding in service.disabled_bindings.values()],
    }


@router.get("/{role_id}")
def get_role_model(role_id: str) -> dict[str, object]:
    service = RoleModelBindingService()
    binding = service.get_binding(role_id)
    disabled = service.get_disabled(role_id)
    if binding is None and disabled is None:
        raise HTTPException(status_code=404, detail="role_model_binding_not_found")
    return {"status": "ok" if binding else "blocked", "binding": binding.model_dump() if binding else None, "disabled": disabled.model_dump() if disabled else None}


@router.get("/{role_id}/binding")
def get_role_model_binding(role_id: str) -> dict[str, object]:
    return get_role_model(role_id)


@router.get("/{role_id}/gate")
def get_role_model_gate(role_id: str) -> dict[str, object]:
    decision = RoleModelGateServiceV2().decide(role_id, RoleInferenceRequest(role_id=role_id))
    return {"status": decision.status, "gate": decision.model_dump()}


@router.get("/{role_id}/status")
def get_role_model_role_status(role_id: str) -> dict[str, object]:
    decision = RoleModelGateServiceV2().decide(role_id, RoleInferenceRequest(role_id=role_id))
    return {"status": decision.status, "role_id": role_id, "gate": decision.model_dump()}


@router.post("/{role_id}/preview")
def preview_role_model(role_id: str, request: RoleInferenceRequest | None = None) -> dict[str, object]:
    result = RoleInferenceService().preview(role_id, _request_for(role_id, request))
    return {"status": result.status, "result": result.model_dump(), "model_invoked": False, "side_effects": False}


@router.post("/{role_id}/run")
def run_role_model(role_id: str, request: RoleInferenceRequest | None = None) -> dict[str, object]:
    result = RoleInferenceService().run(role_id, _request_for(role_id, request))
    return {"status": result.status, "result": result.model_dump(), "side_effects": False}


@router.post("/{role_id}/fallback-preview")
def preview_role_model_fallback(role_id: str, request: RoleInferenceRequest | None = None) -> dict[str, object]:
    binding = RoleModelBindingService().get_binding(role_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="role_model_binding_not_found")
    decision = RoleModelFallbackService().decide(binding, reason="preview")
    return {"status": "ok" if decision.fallback_allowed else "blocked", "fallback": decision.model_dump(), "model_invoked": False}


@router.post("/{role_id}/escalate-preview")
def preview_role_model_escalation(role_id: str, request: RoleInferenceRequest | None = None) -> dict[str, object]:
    binding = RoleModelBindingService().get_binding(role_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="role_model_binding_not_found")
    candidates = binding.escalation_candidates()
    requested = candidates[0] if candidates else None
    escalation_request = _request_for(role_id, request, requested_model_id=requested, manual_escalation=True)
    decision = RoleModelGateServiceV2().decide(role_id, escalation_request, model_id=requested, manual=True)
    return {"status": "requires_manual_confirmation" if not decision.allowed else decision.status, "gate": decision.model_dump(), "model_invoked": False}


@router.post("/{role_id}/escalate-run")
def run_role_model_escalation(role_id: str, request: RoleInferenceRequest | None = None) -> dict[str, object]:
    binding = RoleModelBindingService().get_binding(role_id)
    if binding is None:
        raise HTTPException(status_code=404, detail="role_model_binding_not_found")
    candidates = binding.escalation_candidates()
    requested = (request.requested_model_id if request else None) or (candidates[0] if candidates else None)
    escalation_request = _request_for(role_id, request, requested_model_id=requested, manual_escalation=True)
    result = RoleInferenceService().run(role_id, escalation_request, manual=True)
    return {"status": result.status, "result": result.model_dump(), "side_effects": False}
