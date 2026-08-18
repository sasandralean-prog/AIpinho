from __future__ import annotations

from pathlib import Path

from aipinho.schemas.vision.contracts import MMProjValidationResult
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.vision.config import vision_config


class MMProjPairValidator:
    def __init__(self, registry: ModelRegistryService | None = None) -> None:
        self.registry = registry or ModelRegistryService()
        self.policy = vision_config("mmproj_policy.yaml")

    def validate(self, model_id: str) -> MMProjValidationResult:
        model = self.registry.get_runtime_model(model_id)
        if model is None:
            return MMProjValidationResult(status="blocked", model_id=model_id, blocked_reasons=["model_not_registered"])
        required = model.requires_mmproj or model_id in set(self.policy.get("mmproj", {}).get("required_for", []) or [])
        if not required:
            return MMProjValidationResult(status="ok", model_id=model_id, valid=True)
        blocked: list[str] = []
        path = Path(str(model.mmproj_path or ""))
        if not model.mmproj_path:
            blocked.append("missing_mmproj")
        elif path.suffix.lower() != ".gguf":
            blocked.append("mmproj_not_gguf")
        elif not path.exists():
            blocked.append("mmproj_file_not_found")
        allowed = [str(item).lower() for item in self.policy.get("allowed_roots", []) or []]
        blocked_roots = [str(item).lower() for item in self.policy.get("blocked_roots", []) or []]
        lowered = str(path).lower()
        if model.mmproj_path and allowed and not any(lowered.startswith(root.lower()) for root in allowed):
            blocked.append("mmproj_outside_allowed_roots")
        if any(lowered.startswith(root.lower()) for root in blocked_roots):
            blocked.append("mmproj_forbidden_root")
        return MMProjValidationResult(status="ok" if not blocked else "blocked", model_id=model_id, mmproj_path=model.mmproj_path, valid=not blocked, blocked_reasons=list(dict.fromkeys(blocked)))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "mmproj_pair_validator"}
