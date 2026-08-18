from __future__ import annotations

from aipinho.services.vision.config import vision_config


class ImageInputPolicyService:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or vision_config("image_input_policy.yaml")

    def allowed_extensions(self) -> set[str]:
        return {str(item).lower() for item in self.config.get("allowed_extensions", []) or []}

    def allowed_mime_types(self) -> set[str]:
        return {str(item).lower() for item in self.config.get("allowed_mime_types", []) or []}

    def limits(self) -> dict:
        return self.config.get("limits", {}) if isinstance(self.config.get("limits", {}), dict) else {}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "image_input_policy", "allowed_extensions": sorted(self.allowed_extensions())}
