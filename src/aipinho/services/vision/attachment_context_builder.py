from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextInjectionItem, ContextProvenance
from aipinho.schemas.vision.contracts import OCRResult, VisionAnalysisResult


class AttachmentContextBuilder:
    def from_vision_result(self, result: VisionAnalysisResult) -> list[ContextInjectionItem]:
        items: list[ContextInjectionItem] = []
        for evidence in result.evidence:
            items.append(
                ContextInjectionItem(
                    kind="visual_evidence",
                    source_type="visual_evidence",
                    source_id=evidence.evidence_id,
                    content=evidence.summary,
                    citation_ids=[evidence.citation.citation_id],
                    provenance=ContextProvenance(
                        source_type="visual_evidence",
                        source_id=evidence.evidence_id,
                        citation_id=evidence.citation.citation_id,
                        origin_reason="explicit_visual_context_admission",
                        content_hash=evidence.source_ref.content_hash,
                        source_ref=evidence.source_ref.model_dump(),
                    ),
                    score=evidence.confidence,
                    metadata={"run_id": result.run_id, "confidence": evidence.confidence},
                )
            )
        return items

    def from_ocr_result(self, result: OCRResult) -> list[ContextInjectionItem]:
        items: list[ContextInjectionItem] = []
        for block in result.text_blocks:
            if not block.citation:
                continue
            items.append(
                ContextInjectionItem(
                    kind="ocr_text_block",
                    source_type="ocr_text_block",
                    source_id=block.block_id,
                    content=block.text,
                    citation_ids=[block.citation.citation_id],
                    provenance=ContextProvenance(
                        source_type="ocr_text_block",
                        source_id=block.block_id,
                        citation_id=block.citation.citation_id,
                        origin_reason="explicit_ocr_context_admission",
                        content_hash=block.citation.source_ref.content_hash,
                        source_ref=block.citation.source_ref.model_dump(),
                    ),
                    score=float(block.confidence or 0.0),
                    metadata={"run_id": result.run_id, "confidence": block.confidence, "page": block.page},
                )
            )
        return items

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "attachment_context_builder", "requires_citations": True}
