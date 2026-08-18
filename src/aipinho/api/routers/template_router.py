from __future__ import annotations

from fastapi import APIRouter, HTTPException

from aipinho.services.templates.template_registry_service import TemplateRegistryService
from aipinho.services.templates.template_validator import TemplateValidator

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


def _manifest_card(manifest) -> dict[str, object]:
    return {
        "template_id": manifest.template_id,
        "display_name": manifest.display_name,
        "status": manifest.status,
        "category": manifest.category,
        "description": manifest.description,
        "supported_project_types": manifest.supported_project_types,
        "supported_languages": manifest.supported_languages,
        "supported_platforms": manifest.supported_platforms,
        "risk_level": manifest.risk_level,
        "required_files": manifest.required_files,
        "generated_assets": manifest.generated_assets,
        "artifact_policy": manifest.artifact_policy,
    }


@router.get("/status")
def templates_status() -> dict[str, object]:
    return TemplateRegistryService().health().model_dump()


@router.get("")
def list_templates(include_experimental: bool = True) -> dict[str, object]:
    registry = TemplateRegistryService()
    templates = registry.list_templates(include_disabled=False)
    if not include_experimental:
        templates = [item for item in templates if item.status == "active"]
    return {"ok": True, "templates": [_manifest_card(item) for item in templates]}


@router.get("/{template_id}")
def get_template(template_id: str) -> dict[str, object]:
    manifest = TemplateRegistryService().get(template_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    validation = TemplateValidator().validate_manifest(manifest)
    return {"ok": True, "template": manifest.model_dump(), "validation": validation}


@router.post("/validate/{template_id}")
def validate_template(template_id: str) -> dict[str, object]:
    manifest = TemplateRegistryService().get(template_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="template_not_found")
    return {"ok": True, "validation": TemplateValidator().validate_manifest(manifest)}


@router.get("/mobile/view-model")
def templates_mobile_view_model() -> dict[str, object]:
    registry = TemplateRegistryService()
    templates = registry.list_templates(include_disabled=False)
    return {
        "ok": True,
        "screen": "templates",
        "title": "Templates Sandbox",
        "status": registry.health().model_dump(),
        "cards": [_manifest_card(item) for item in templates],
        "raw_default_visible": False,
    }
