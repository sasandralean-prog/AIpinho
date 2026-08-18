from __future__ import annotations

from aipinho.services.vision.config import vision_config


class ImagePreprocessingPolicyService:
    def __init__(self) -> None:
        self.config = vision_config("image_preprocessing_policy.yaml")

    def status(self) -> dict[str, object]:
        preprocessing = self.config.get("preprocessing", {}) if isinstance(self.config.get("preprocessing", {}), dict) else {}
        return {"status": "ok", "service": "image_preprocessing_policy", "store_raw_blob": bool(preprocessing.get("store_raw_blob", False))}
