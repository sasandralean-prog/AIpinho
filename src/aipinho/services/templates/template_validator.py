from __future__ import annotations

from aipinho.schemas.templates import TemplateManifest


class TemplateValidator:
    REQUIRED_FIELDS = {
        "template_id",
        "display_name",
        "slug",
        "version",
        "category",
        "description",
        "generator_key",
    }

    def validate_manifest(self, manifest: TemplateManifest) -> dict[str, object]:
        errors: list[str] = []
        warnings: list[str] = []
        payload = manifest.model_dump()
        for field in self.REQUIRED_FIELDS:
            if not payload.get(field):
                errors.append(f"missing_field:{field}")
        if manifest.status == "active":
            if not manifest.required_files:
                errors.append("active_template_requires_required_files")
            if "PROJECT_MANIFEST.json" not in manifest.required_files:
                errors.append("active_template_requires_project_manifest")
            if "README.md" not in manifest.required_files:
                errors.append("active_template_requires_readme")
            if not manifest.validation_profile:
                errors.append("active_template_requires_validation_profile")
        if manifest.risk_level not in {"low", "medium", "high", "critical"}:
            errors.append("invalid_risk_level")
        if manifest.status == "experimental":
            warnings.append("experimental_template")
        return {
            "valid": not errors,
            "status": "valid" if not errors else "invalid",
            "errors": errors,
            "warnings": warnings,
            "template_id": manifest.template_id,
        }
