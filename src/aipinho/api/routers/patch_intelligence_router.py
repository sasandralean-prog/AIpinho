from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.schemas.patch_intelligence import IntelligentPatchProposalRequest, PatchKnowledgeQuery, PatchPatternRecognitionRequest
from aipinho.services.patch_intelligence_service import IntelligentPatchProposalService, PatchKnowledgeQueryService, PatchPatternEngine


router = APIRouter(prefix="/api/v1/runtime/patch-intelligence", tags=["patch-intelligence"])


@router.get("/status")
def status() -> dict[str, object]:
    return PatchKnowledgeQueryService().status()


@router.get("/knowledge")
def list_knowledge() -> dict[str, object]:
    return PatchKnowledgeQueryService().list_entries().model_dump(mode="json")


@router.get("/knowledge/{entry_id}")
def get_knowledge(entry_id: str) -> dict[str, object]:
    entry = PatchKnowledgeQueryService().get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="patch_knowledge_entry_not_found")
    return entry.model_dump(mode="json")


@router.post("/query")
def query_knowledge(request: PatchKnowledgeQuery) -> dict[str, object]:
    return PatchKnowledgeQueryService().query(request).model_dump(mode="json")


@router.get("/patterns")
def patterns_status() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "patch_pattern_engine",
        "deterministic": True,
        "prompt_used": False,
        "text_full_match_used": False,
    }


@router.post("/patterns")
def recognize_patterns(request: PatchPatternRecognitionRequest) -> dict[str, object]:
    return PatchPatternEngine().recognize(request).model_dump(mode="json")


@router.post("/proposal")
def create_proposal(request: IntelligentPatchProposalRequest) -> dict[str, object]:
    return IntelligentPatchProposalService().create(request).model_dump(mode="json")


@router.get("/proposal/{proposal_id}")
def get_proposal(proposal_id: str) -> dict[str, object]:
    proposal = IntelligentPatchProposalService().get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="intelligent_patch_proposal_not_found")
    return proposal.model_dump(mode="json")
