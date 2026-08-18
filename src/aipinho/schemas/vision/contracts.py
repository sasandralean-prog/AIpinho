from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


VisionStatusValue = Literal["completed", "accepted", "accepted_with_warnings", "degraded", "blocked", "rejected"]
ImageSourceType = Literal["uploaded_image", "workspace_image", "document_page", "screenshot", "diagram", "test_fixture"]


class ImageRegion(AIpinhoModel):
    region_id: str = Field(default_factory=lambda: f"image_region_{uuid4().hex}")
    page: int | None = None
    frame: int | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    label: str | None = None


class ImageSourceRef(AIpinhoModel):
    image_id: str = Field(default_factory=lambda: f"image_{uuid4().hex}")
    source_type: ImageSourceType = "uploaded_image"
    path: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    page: int | None = None
    content_hash: str | None = None
    origin: str = "explicit_user_request"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageInput(AIpinhoModel):
    source_ref: ImageSourceRef | None = None
    declared_purpose: str = "vision_analysis"
    scope: str = "user_request"
    mime_type: str | None = None
    file_path: str | None = None
    file_name: str | None = None
    file_size_bytes: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImageInputValidation(AIpinhoModel):
    status: str
    allowed: bool = False
    input: ImageInput | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class ImageCitation(AIpinhoModel):
    citation_id: str = Field(default_factory=lambda: f"image_citation_{uuid4().hex}")
    image_id: str
    source_ref: ImageSourceRef
    region: ImageRegion | None = None
    citation_type: str = "image_region"
    summary: str = ""
    confidence: float = 0.0
    created_at: str = Field(default_factory=utc_now)


class VisualFinding(AIpinhoModel):
    finding_id: str = Field(default_factory=lambda: f"visual_finding_{uuid4().hex}")
    finding_type: str = "observation"
    summary: str
    confidence: float = 0.0
    citation_id: str | None = None
    region: ImageRegion | None = None
    warnings: list[str] = Field(default_factory=list)


class VisualEvidence(AIpinhoModel):
    evidence_id: str = Field(default_factory=lambda: f"visual_evidence_{uuid4().hex}")
    evidence_type: str = "visual_summary"
    summary: str
    source_ref: ImageSourceRef
    citation: ImageCitation
    confidence: float = 0.0
    raw_blob_included: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class VisionAnalysisRequest(AIpinhoModel):
    image: ImageInput | None = None
    prompt: str = ""
    purpose: str = "image_understanding"
    requested_model_id: str | None = None
    allow_fallback: bool = True
    include_trace: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisionAnalysisHit(AIpinhoModel):
    hit_id: str = Field(default_factory=lambda: f"vision_hit_{uuid4().hex}")
    summary: str
    confidence: float
    citation: ImageCitation
    evidence_id: str | None = None


class VisionAnalysisResult(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"vision_run_{uuid4().hex}")
    status: VisionStatusValue
    model_id: str | None = None
    provider_id: str | None = None
    fallback_used: bool = False
    summary: str = ""
    findings: list[VisualFinding] = Field(default_factory=list)
    evidence: list[VisualEvidence] = Field(default_factory=list)
    citations: list[ImageCitation] = Field(default_factory=list)
    hits: list[VisionAnalysisHit] = Field(default_factory=list)
    raw_output_hidden: bool = True
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    evaluation: dict[str, Any] = Field(default_factory=dict)


class UIInspectionRequest(VisionAnalysisRequest):
    purpose: str = "ui_inspection"


class UIInspectionResult(VisionAnalysisResult):
    ui_elements: list[dict[str, Any]] = Field(default_factory=list)


class DiagramAnalysisResult(VisionAnalysisResult):
    diagram_elements: list[dict[str, Any]] = Field(default_factory=list)


class DocumentPageRef(AIpinhoModel):
    document_id: str = Field(default_factory=lambda: f"document_{uuid4().hex}")
    page: int = 1
    source_ref: ImageSourceRef


class OCRConfidence(AIpinhoModel):
    value: float
    status: str = "estimated"
    warning: str | None = None


class OCRCitation(AIpinhoModel):
    citation_id: str = Field(default_factory=lambda: f"ocr_citation_{uuid4().hex}")
    source_ref: ImageSourceRef
    page_ref: DocumentPageRef | None = None
    region: ImageRegion | None = None
    excerpt: str
    confidence: float
    created_at: str = Field(default_factory=utc_now)


class OCRTextBlock(AIpinhoModel):
    block_id: str = Field(default_factory=lambda: f"ocr_block_{uuid4().hex}")
    text: str
    confidence: float | None = None
    page: int | None = None
    region: ImageRegion | None = None
    citation: OCRCitation | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class OCRRequest(AIpinhoModel):
    image: ImageInput | None = None
    prompt: str = ""
    requested_model_id: str | None = None
    include_trace: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class OCRResult(AIpinhoModel):
    run_id: str = Field(default_factory=lambda: f"ocr_run_{uuid4().hex}")
    status: VisionStatusValue
    model_id: str | None = None
    provider_id: str | None = None
    text_blocks: list[OCRTextBlock] = Field(default_factory=list)
    citations: list[OCRCitation] = Field(default_factory=list)
    summary: str = ""
    raw_output_hidden: bool = True
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now)
    evaluation: dict[str, Any] = Field(default_factory=dict)


class DocumentReadRequest(OCRRequest):
    max_pages: int | None = None


class DocumentReadResult(OCRResult):
    pages_processed: int = 0
    partial: bool = False


class VisionContextItem(AIpinhoModel):
    context_item_id: str = Field(default_factory=lambda: f"vision_context_{uuid4().hex}")
    content: str
    source_ref: ImageSourceRef
    citation: ImageCitation
    confidence: float
    safe_for_prompt_assembly: bool = False


class OCRContextItem(AIpinhoModel):
    context_item_id: str = Field(default_factory=lambda: f"ocr_context_{uuid4().hex}")
    content: str
    source_ref: ImageSourceRef
    citation: OCRCitation
    confidence: float
    safe_for_prompt_assembly: bool = False


class MultimodalModelProfile(AIpinhoModel):
    model_id: str
    provider_id: str
    modality: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    requires_mmproj: bool = False
    mmproj_path: str | None = None


class MMProjValidationResult(AIpinhoModel):
    status: str
    model_id: str
    mmproj_path: str | None = None
    valid: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class VisionModelRun(AIpinhoModel):
    run_id: str
    model_id: str
    provider_id: str
    status: str
    real_runtime_attempted: bool = False
    deterministic_fallback_used: bool = True


class OCRModelRun(VisionModelRun):
    pass


class VisionRAGIngestionRequest(AIpinhoModel):
    result: VisionAnalysisResult | OCRResult | None = None
    target_namespace: str = "vision_rag"
    include_trace: bool = True


class VisionRAGQueryRequest(AIpinhoModel):
    query: str
    namespace: Literal["vision_rag", "ocr_rag"] = "vision_rag"
    top_k: int = 5
    include_trace: bool = True


class VisionTrace(AIpinhoModel):
    trace_id: str
    events: list[dict[str, Any]] = Field(default_factory=list)


class VisionAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"vision_audit_{uuid4().hex}")
    event_type: str
    status: str
    run_id: str | None = None
    source_id: str | None = None
    model_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class VisionStatus(AIpinhoModel):
    enabled: bool = True
    vision_runtime_enabled: bool = True
    ocr_runtime_enabled: bool = True
    primary_vision_model: str = "qwen2_5_vl_7b_q4_k_m"
    vision_fallback_model: str = "llava_v1_6_mistral_7b_q4_k_m"
    ocr_model: str = "nanonets_ocr_s_q5_k_m"
    vision_rag_enabled: bool = True
    ocr_rag_enabled: bool = True
    raw_image_memory_enabled: bool = False
    raw_image_vector_ingestion_enabled: bool = False
    auto_memory_from_image_enabled: bool = False
    auto_rag_from_image_enabled: bool = False
    tool_calling_enabled: bool = False
    workspace_source_mutation_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
