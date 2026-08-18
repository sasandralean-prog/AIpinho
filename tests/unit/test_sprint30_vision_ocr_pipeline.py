from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextAdmissionRequest, ContextInjectionItem, ContextProvenance, RAGMemoryPolicyDecision
from aipinho.schemas.vision.contracts import ImageInput, ImageSourceRef, OCRRequest, VisionAnalysisRequest, VisionRAGIngestionRequest, VisionRAGQueryRequest, DocumentReadRequest
from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
from aipinho.services.vision.attachment_context_builder import AttachmentContextBuilder
from aipinho.services.vision.diagram_analysis_service import DiagramAnalysisService
from aipinho.services.vision.document_image_reader_service import DocumentImageReaderService
from aipinho.services.vision.mmproj_pair_validator import MMProjPairValidator
from aipinho.services.vision.ocr_pipeline_service import OCRPipelineService
from aipinho.services.vision.ui_inspection_service import UIInspectionService
from aipinho.services.vision.vision_analysis_service import VisionAnalysisService
from aipinho.services.vision.vision_rag_ingestion_preview_service import VisionRAGIngestionPreviewService
from aipinho.services.vision.vision_rag_query_service import VisionRAGQueryService
from aipinho.services.vision.vision_status_service import VisionStatusService


def image_input(tmp_path, name: str = "screen.png") -> ImageInput:
    path = tmp_path / name
    path.write_bytes(b"fake image bytes")
    source = ImageSourceRef(source_type="test_fixture", path=str(path), file_name=name, mime_type="image/png", content_hash="a" * 64)
    return ImageInput(source_ref=source, file_path=str(path), file_name=name, mime_type="image/png", file_size_bytes=path.stat().st_size)


def test_vision_requires_source_ref():
    result = VisionAnalysisService().analyze(VisionAnalysisRequest(image=ImageInput(file_name="screen.png", mime_type="image/png")))

    assert result.status == "blocked"
    assert "missing_source_ref" in result.blocked_reasons
    assert result.raw_output_hidden is True


def test_vision_analysis_has_citation_evidence_confidence_trace_and_evaluation(tmp_path):
    result = VisionAnalysisService().analyze(VisionAnalysisRequest(image=image_input(tmp_path), prompt="describe"))

    assert result.status in {"completed", "degraded"}
    assert result.citations
    assert result.evidence
    assert result.findings[0].confidence > 0
    assert result.trace_id
    assert result.evaluation["status"] in {"accepted", "accepted_with_warnings"}
    assert result.raw_output_hidden is True
    assert result.evidence[0].raw_blob_included is False


def test_ui_inspection_and_diagram_analysis_return_cited_structures(tmp_path):
    ui = UIInspectionService().inspect(VisionAnalysisRequest(image=image_input(tmp_path, "ui.png")))
    diagram = DiagramAnalysisService().analyze(VisionAnalysisRequest(image=image_input(tmp_path, "diagram.png")))

    assert ui.status in {"completed", "degraded"}
    assert ui.ui_elements[0]["citation_id"] == ui.citations[0].citation_id
    assert diagram.status in {"completed", "degraded"}
    assert diagram.diagram_elements[0]["confidence"] > 0


def test_ocr_requires_source_ref():
    result = OCRPipelineService().extract(OCRRequest(image=ImageInput(file_name="doc.png", mime_type="image/png"), metadata={"mock_text": "hello"}))

    assert result.status == "blocked"
    assert "missing_source_ref" in result.blocked_reasons


def test_ocr_result_has_citation_confidence_trace_and_evaluation(tmp_path):
    result = OCRPipelineService().extract(OCRRequest(image=image_input(tmp_path, "doc.png"), metadata={"mock_text": "Invoice total: 42", "confidence": 0.91}))

    assert result.status == "completed"
    assert result.text_blocks[0].confidence == 0.91
    assert result.text_blocks[0].citation is not None
    assert result.citations[0].excerpt.startswith("Invoice")
    assert result.trace_id
    assert result.evaluation["status"] == "accepted"
    assert result.raw_output_hidden is True


def test_ocr_low_confidence_is_degraded_but_cited(tmp_path):
    result = OCRPipelineService().extract(OCRRequest(image=image_input(tmp_path, "low.png"), metadata={"mock_text": "hard to read", "confidence": 0.2}))

    assert result.status == "degraded"
    assert "confidence_below_minimum" in result.warnings
    assert result.citations


def test_ocr_secret_like_text_is_blocked(tmp_path):
    result = OCRPipelineService().extract(OCRRequest(image=image_input(tmp_path, "secret.png"), metadata={"mock_text": "OPENAI_API_KEY=sk-1234567890abcdef"}))

    assert result.status == "blocked"
    assert "secret_ocr_text_blocked" in result.blocked_reasons


def test_document_reader_respects_page_limit(tmp_path):
    image = image_input(tmp_path, "book.pdf")
    image.source_ref.mime_type = "application/pdf"
    image.mime_type = "application/pdf"
    image.metadata["page_count"] = 5
    result = DocumentImageReaderService().read(DocumentReadRequest(image=image, max_pages=2, metadata={"mock_text": "page text", "confidence": 0.8}))

    assert result.pages_processed == 2
    assert result.partial is True
    assert "document_page_limit_applied" in result.warnings


def test_attachment_context_builder_creates_cited_items(tmp_path):
    vision = VisionAnalysisService().analyze(VisionAnalysisRequest(image=image_input(tmp_path, "ctx.png")))
    ocr = OCRPipelineService().extract(OCRRequest(image=image_input(tmp_path, "ctx_ocr.png"), metadata={"mock_text": "context text", "confidence": 0.8}))
    builder = AttachmentContextBuilder()

    vision_items = builder.from_vision_result(vision)
    ocr_items = builder.from_ocr_result(ocr)

    assert vision_items[0].kind == "visual_evidence"
    assert vision_items[0].citation_ids
    assert ocr_items[0].kind == "ocr_text_block"
    assert ocr_items[0].citation_ids


def test_context_admission_blocks_visual_attachment_without_citation():
    item = ContextInjectionItem(
        kind="visual_evidence",
        source_type="visual_evidence",
        source_id="evidence_missing_citation",
        content="visual claim",
        citation_ids=[],
        provenance=ContextProvenance(source_type="visual_evidence", source_id="evidence_missing_citation", citation_id="", origin_reason="test"),
    )
    policy = RAGMemoryPolicyDecision(usage_mode="explicit_user_request", allowed=True, status="allowed", allow_retrieval=True)
    decision = ContextAdmissionService().admit(ContextAdmissionRequest(policy_decision=policy, attachment_context_items=[item.model_dump()]))

    assert decision.status == "blocked"
    assert "attachment_context_missing_citation" in decision.blocked_reasons


def test_vision_rag_preview_requires_governed_result_and_never_writes(tmp_path):
    result = VisionAnalysisService().analyze(VisionAnalysisRequest(image=image_input(tmp_path, "rag.png")))
    preview = VisionRAGIngestionPreviewService().preview(VisionRAGIngestionRequest(result=result, target_namespace="vision_rag"))

    assert preview.status == "ready"
    assert preview.approval_required is True
    assert preview.would_write_index is False
    assert preview.chunk_count > 0


def test_ocr_rag_preview_uses_ocr_namespace_and_never_writes(tmp_path):
    result = OCRPipelineService().extract(OCRRequest(image=image_input(tmp_path, "rag_ocr.png"), metadata={"mock_text": "cited OCR text", "confidence": 0.8}))
    preview = VisionRAGIngestionPreviewService().preview(VisionRAGIngestionRequest(result=result, target_namespace="ocr_rag"))

    assert preview.status == "ready"
    assert preview.namespace_id == "ocr_rag"
    assert preview.would_write_index is False


def test_vision_rag_query_is_scoped_to_vision_or_ocr_namespace():
    result = VisionRAGQueryService().query(VisionRAGQueryRequest(query="nothing indexed yet", namespace="vision_rag", top_k=2))

    assert result.status in {"found", "partial", "no_results", "blocked"}
    assert result.query == "nothing indexed yet"


def test_vision_status_flags_are_governed_and_no_raw_memory():
    status = VisionStatusService().status()

    assert status["vision_runtime_enabled"] is True
    assert status["ocr_runtime_enabled"] is True
    assert status["raw_image_memory_enabled"] is False
    assert status["raw_image_vector_ingestion_enabled"] is False
    assert status["auto_memory_from_image_enabled"] is False


def test_mmproj_validator_accepts_registered_llava_pair():
    result = MMProjPairValidator().validate("llava_v1_6_mistral_7b_q4_k_m")

    assert result.valid is True
    assert result.blocked_reasons == []

