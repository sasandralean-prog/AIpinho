from __future__ import annotations

from aipinho.schemas.models.model_doctor_request import ModelDoctorRequest
from aipinho.services.models.model_doctor_service import ModelDoctorService
from aipinho.services.vision.mmproj_pair_validator import MMProjPairValidator
from aipinho.services.vision.vision_model_registry import VisionModelRegistry


class MultimodalModelDoctor:
    def __init__(self, doctor: ModelDoctorService | None = None, registry: VisionModelRegistry | None = None) -> None:
        self.doctor_service = doctor or ModelDoctorService()
        self.registry = registry or VisionModelRegistry()
        self.mmproj = MMProjPairValidator()

    def doctor(self, model_id: str) -> dict[str, object]:
        result = self.doctor_service.run_for_model(model_id, ModelDoctorRequest(include_first_token_probe=False, include_trace=True))
        if result is None:
            return {"status": "blocked", "model_id": model_id, "blocked_reasons": ["model_not_registered"]}
        payload = result.model_dump()
        mmproj = self.mmproj.validate(model_id)
        payload["mmproj_validation"] = mmproj.model_dump()
        if not mmproj.valid:
            payload["status"] = "blocked"
            payload["blocked_reasons"] = list(dict.fromkeys([*payload.get("blocked_reasons", []), *mmproj.blocked_reasons]))
        return payload

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "multimodal_model_doctor", "models": [item.model_id for item in self.registry.models()]}

