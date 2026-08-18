from __future__ import annotations

from aipinho.schemas.vision.contracts import VisionStatus
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.services.vision.config import vision_config
from aipinho.services.vision.ocr_model_gate_service import OCRModelGateService
from aipinho.services.vision.vision_model_gate_service import VisionModelGateService
from aipinho.services.vision.vision_model_registry import VisionModelRegistry


class VisionStatusService:
    def __init__(self) -> None:
        self.config = vision_config("vision_policy.yaml")
        self.registry = VisionModelRegistry()
        self.vision_gate = VisionModelGateService()
        self.ocr_gate = OCRModelGateService()
        self.vector_status = VectorRAGStatusService()

    def status_model(self) -> VisionStatus:
        models = self.config.get("models", {}) if isinstance(self.config.get("models", {}), dict) else {}
        vector = self.vector_status.status_model()
        vision = self.vision_gate.decide()
        ocr = self.ocr_gate.decide()
        warnings = [*list(vision.get("warnings", [])), *list(ocr.get("warnings", [])), *vector.warnings]
        blocked = [*list(vision.get("blocked_reasons", [])), *list(ocr.get("blocked_reasons", [])), *vector.blocked_reasons]
        return VisionStatus(
            enabled=bool(self.config.get("enabled", True)),
            vision_runtime_enabled=True,
            ocr_runtime_enabled=True,
            primary_vision_model=str(models.get("primary_vision_model", self.registry.primary_vision_model_id())),
            vision_fallback_model=str(models.get("fallback_vision_model", self.registry.fallback_vision_model_id())),
            ocr_model=str(models.get("ocr_model", self.registry.ocr_model_id())),
            vision_rag_enabled=True,
            ocr_rag_enabled=True,
            raw_image_memory_enabled=False,
            raw_image_vector_ingestion_enabled=False,
            auto_memory_from_image_enabled=False,
            auto_rag_from_image_enabled=False,
            tool_calling_enabled=False,
            workspace_source_mutation_enabled=False,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked)),
        )

    def status(self) -> dict[str, object]:
        model = self.status_model()
        return {"status": "ok" if not model.blocked_reasons else "degraded", "service": "vision_status", **model.model_dump()}

