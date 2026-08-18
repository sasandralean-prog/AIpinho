from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.debugger.inspectors.context_plan_inspector import ContextPlanInspector
from aipinho.services.debugger.inspectors.memory_usage_inspector import MemoryUsageInspector
from aipinho.services.debugger.inspectors.model_run_inspector import ModelRunInspector
from aipinho.services.debugger.inspectors.ocr_run_inspector import OCRRunInspector
from aipinho.services.debugger.inspectors.output_evaluation_inspector import OutputEvaluationInspector
from aipinho.services.debugger.inspectors.patch_apply_inspector import PatchApplyInspector
from aipinho.services.debugger.inspectors.rag_ingestion_inspector import RAGIngestionInspector
from aipinho.services.debugger.inspectors.rag_run_inspector import RAGRunInspector
from aipinho.services.debugger.inspectors.role_run_inspector import RoleRunInspector
from aipinho.services.debugger.inspectors.validation_inspector import ValidationInspector
from aipinho.services.debugger.inspectors.vision_run_inspector import VisionRunInspector

router = APIRouter(prefix="/api/v1/debugger", tags=["debugger-inspectors"])


@router.get("/model-runs/{run_id}")
def inspect_model_run(run_id: str) -> dict[str, object]:
    result = ModelRunInspector().inspect(run_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/role-runs/{run_id}")
def inspect_role_run(run_id: str) -> dict[str, object]:
    result = RoleRunInspector().inspect(run_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/rag-runs/{query_id}")
def inspect_rag_run(query_id: str) -> dict[str, object]:
    result = RAGRunInspector().inspect(query_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/rag-ingestions/{ingestion_id}")
def inspect_rag_ingestion(ingestion_id: str) -> dict[str, object]:
    result = RAGIngestionInspector().inspect(ingestion_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/context-plans/{plan_id}")
def inspect_context_plan(plan_id: str) -> dict[str, object]:
    result = ContextPlanInspector().inspect(plan_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/memory-usage/{memory_id}")
def inspect_memory_usage(memory_id: str) -> dict[str, object]:
    result = MemoryUsageInspector().inspect(memory_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/vision-runs/{run_id}")
def inspect_vision_run(run_id: str) -> dict[str, object]:
    result = VisionRunInspector().inspect(run_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/ocr-runs/{run_id}")
def inspect_ocr_run(run_id: str) -> dict[str, object]:
    result = OCRRunInspector().inspect(run_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/patch-apply-runs/{apply_run_id}")
def inspect_patch_apply(apply_run_id: str) -> dict[str, object]:
    result = PatchApplyInspector().inspect(apply_run_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/validations/{validation_id}")
def inspect_validation(validation_id: str) -> dict[str, object]:
    result = ValidationInspector().inspect(validation_id)
    return {"status": result.status, "inspection": result.model_dump()}


@router.get("/evaluations/{evaluation_id}")
def inspect_evaluation(evaluation_id: str) -> dict[str, object]:
    result = OutputEvaluationInspector().inspect(evaluation_id)
    return {"status": result.status, "inspection": result.model_dump()}
