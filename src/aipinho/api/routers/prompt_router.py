from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class OutputContractValidationRequest(BaseModel):
    contract_type: str = "plain_text"
    content: str = ""


@router.get("/status")
def get_prompt_status() -> dict[str, object]:
    return PromptAssemblyService().status()


@router.post("/assemble")
def assemble_prompt(request: PromptAssemblyRequest) -> dict[str, object]:
    assembly = PromptAssemblyService().assemble(request)
    return {"status": "ok", "assembly": assembly.model_dump(), "invokes_model": False, "side_effects": False}


@router.post("/preview")
def preview_prompt(request: PromptAssemblyRequest) -> dict[str, object]:
    preview = PromptAssemblyService().preview(request)
    return {"status": "ok", "preview": preview.model_dump()}


@router.post("/estimate-budget")
def estimate_budget(request: PromptAssemblyRequest) -> dict[str, object]:
    return PromptAssemblyService().estimate_budget(request)


@router.post("/validate-output-contract")
def validate_output_contract(request: OutputContractValidationRequest) -> dict[str, object]:
    return PromptAssemblyService().validate_output_contract(request.contract_type, request.content)
