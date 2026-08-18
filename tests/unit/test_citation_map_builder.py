from aipinho.services.context.context_core import CitationMapBuilder, ContextAdmissionServiceV2, ContextBundleBuilder
from tests.unit.context_test_helpers import request, candidate

def test_citation_map_rag_memory_ocr_image():
    req=request(purpose='report_generation', candidates=[candidate(), candidate(layer='vision_ocr_context',source_type='visual_evidence',source_id='img')])
    decisions=ContextAdmissionServiceV2().admit(req, req.candidates); bundle=ContextBundleBuilder().build(req, req.candidates, decisions)
    assert CitationMapBuilder().build(bundle.items)
