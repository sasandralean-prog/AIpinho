from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.promotion import PromotionApplyRequest, PromotionApprovalRequest, PromotionPlanRequest
from aipinho.services.promotion.promotion_pipeline_service import PromotionPipelineService

router = APIRouter(prefix="/api/v1/promotion", tags=["promotion"])


def _dump(model) -> dict[str, object]:
    return model.model_dump() if hasattr(model, "model_dump") else dict(model)


@router.get("/status")
def promotion_status() -> dict[str, object]:
    return PromotionPipelineService().status()


@router.post("/plans")
def create_promotion_plan(request: PromotionPlanRequest) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().create_plan(request))
    except (FileNotFoundError, ValueError, PermissionError) as exc:
        raise HTTPException(status_code=409, detail={"ok": False, "reason_code": str(exc) or type(exc).__name__}) from exc


@router.get("/plans/{promotion_plan_id}")
def get_promotion_plan(promotion_plan_id: str) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().get_plan(promotion_plan_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="promotion_plan_not_found") from exc


@router.post("/plans/{promotion_plan_id}/preview")
def create_promotion_preview(promotion_plan_id: str) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().create_preview(promotion_plan_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="promotion_plan_not_found") from exc


@router.get("/previews/{preview_id}")
def get_promotion_preview(preview_id: str) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().get_preview(preview_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="promotion_preview_not_found") from exc


@router.post("/approvals")
def approve_promotion(request: PromotionApprovalRequest) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().approve(request))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="promotion_preview_not_found") from exc


@router.post("/apply")
def apply_promotion(request: PromotionApplyRequest) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().apply(request))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="promotion_preview_not_found") from exc


@router.get("/applies/{apply_id}")
def get_promotion_apply(apply_id: str) -> dict[str, object]:
    try:
        return _dump(PromotionPipelineService().get_apply(apply_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="promotion_apply_not_found") from exc
