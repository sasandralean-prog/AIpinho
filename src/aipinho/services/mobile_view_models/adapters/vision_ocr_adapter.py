from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class VisionOcrAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("vision_ocr", ["/api/v1/vision/status", "/api/v1/ocr/status", "/api/v1/vision-rag/status"], "unknown", "Vision/OCR aparecem como evidencia multimodal rastreavel.")

