from __future__ import annotations
from fastapi import APIRouter, HTTPException
from aipinho.services.interaction.raw_copy_service import RawCopyService
from aipinho.services.interaction.raw_search_service import RawSearchService
from aipinho.services.interaction.raw_viewer_service import RawViewerService
router=APIRouter(prefix="/api/v1/raw",tags=["raw"])
@router.get("/{raw_ref_id}/viewer")
def raw_viewer(raw_ref_id:str)->dict[str,object]:
    try: return RawViewerService().viewer(raw_ref_id).model_dump()
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail="raw_not_found") from exc
@router.get("/{raw_ref_id}/search")
def raw_search(raw_ref_id:str,query:str="")->dict[str,object]:
    try: return RawSearchService().search(raw_ref_id,query).model_dump()
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail="raw_not_found") from exc
@router.get("/{raw_ref_id}/copy")
def raw_copy(raw_ref_id:str)->dict[str,object]:
    try: return RawCopyService().copy(raw_ref_id).model_dump()
    except FileNotFoundError as exc: raise HTTPException(status_code=404,detail="raw_not_found") from exc
