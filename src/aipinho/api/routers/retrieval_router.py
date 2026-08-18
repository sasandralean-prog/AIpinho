from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from aipinho.services.rag.retrieval_service import RetrievalService

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


@router.get("/status")
def retrieval_status() -> dict[str, Any]:
    return RetrievalService().status()
