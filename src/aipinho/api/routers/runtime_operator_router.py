from __future__ import annotations

from fastapi import APIRouter

from aipinho.schemas.runtime.runtime_operator import (
    FireTestDoctorAnalyzeRequest,
    RuntimeDoctorAnalyzeRequest,
    RuntimeDoctorExplainRequest,
    RuntimeDoctorPatchPlanRequest,
    RuntimeOperatorSnapshotRequest,
)
from aipinho.services.runtime.runtime_operator_doctor_service import FireTestDoctorService, RuntimeExplainerService, RuntimeOperatorDoctorService, RuntimePatchPlannerService
from aipinho.services.runtime.runtime_operator_service import RuntimeOperatorService


router = APIRouter(prefix="/api/v1/runtime", tags=["runtime-operator"])


@router.get("/operator/status")
def status() -> dict[str, object]:
    return RuntimeOperatorService().status()


@router.get("/doctor")
def doctor_status() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "runtime_doctor",
        "read_only": True,
        "side_effects": False,
        "domains": [
            "Intent",
            "Workspace",
            "Lifecycle",
            "Artifacts",
            "Approval",
            "Validation",
            "Completion",
            "SpeakerTruth",
            "Dispatcher",
            "Timeline",
            "ExecutionPlan",
            "Contracts",
            "Roles",
            "Executor",
            "Models",
            "Tools",
            "Skills",
        ],
        "endpoints": [
            "/api/v1/runtime/doctor/analyze",
            "/api/v1/runtime/doctor/patch-plan",
            "/api/v1/runtime/firetest/analyze",
        ],
    }


@router.get("/operator/snapshot")
def snapshot(task_run_id: str | None = None) -> dict[str, object]:
    return RuntimeOperatorService().snapshot(task_run_id=task_run_id).model_dump(mode="json")


@router.post("/operator/snapshot")
def snapshot_from_payload(request: RuntimeOperatorSnapshotRequest) -> dict[str, object]:
    return RuntimeOperatorService().snapshot(task_run_id=request.task_run_id, runtime_data=request.runtime_data).model_dump(mode="json")


@router.post("/doctor/analyze")
def analyze(request: RuntimeDoctorAnalyzeRequest) -> dict[str, object]:
    snapshot_obj = request.snapshot or RuntimeOperatorService().snapshot(task_run_id=request.task_run_id, runtime_data=request.runtime_data)
    return RuntimeOperatorDoctorService().analyze(snapshot_obj, request.expected).model_dump(mode="json")


@router.post("/doctor/explain")
def explain(request: RuntimeDoctorExplainRequest) -> dict[str, object]:
    return RuntimeExplainerService().explain(request.report, snapshot=request.snapshot).model_dump(mode="json")


@router.post("/doctor/patch-plan")
def patch_plan(request: RuntimeDoctorPatchPlanRequest) -> dict[str, object]:
    return RuntimePatchPlannerService().plan(request.report, source_hints=request.source_hints).model_dump(mode="json")


@router.post("/firetest/analyze")
def analyze_firetest(request: FireTestDoctorAnalyzeRequest) -> dict[str, object]:
    return FireTestDoctorService().analyze(request.raw, request.expected, source_hints=request.source_hints).model_dump(mode="json")
